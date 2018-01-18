import numpy as np
from Orange.data.util import SharedComputeValue
from scipy.interpolate import interp1d

from orangecontrib.spectroscopy.data import getx


def is_increasing(a):
    return np.all(np.diff(a) >= 0)


class SelectColumn(SharedComputeValue):

    def __init__(self, feature, commonfn):
        super().__init__(commonfn)
        self.feature = feature

    def compute(self, data, common):
        return common[:, self.feature]


class CommonDomain:
    """A utility class that helps constructing common transformation for
    SharedComputeValue features. It does the domain transformation
    (input domain needs to be the same as it was with training data).
    """
    def __init__(self, domain):
        self.domain = domain

    def __call__(self, data):
        data = self.transform_domain(data)
        return self.transformed(data)

    def transform_domain(self, data):
        if data.domain != self.domain:
            data = data.from_table(self.domain, data)
        return data

    def transformed(self, data):
        raise NotImplemented


class CommonDomainOrder(CommonDomain):
    """CommonDomain + it also handles wavenumber order.
    """
    def __call__(self, data):
        data = self.transform_domain(data)

        # order X by wavenumbers
        xs, xsind, mon, X = transform_to_sorted_features(data)

        # do the transformation
        X = self.transformed(X, xs[xsind])

        # restore order
        return transform_back_to_features(xsind, mon, X)

    def transformed(self, X, wavenumbers):
        raise NotImplemented


class CommonDomainOrderUnknowns(CommonDomainOrder):
    """CommonDomainOrder + it also handles unknown values: it interpolates
    values before computation and afterwards sets them back to unknown.
    """
    def __call__(self, data):
        data = self.transform_domain(data)

        # order X by wavenumbers
        xs, xsind, mon, X = transform_to_sorted_features(data)

        # interpolates unknowns
        X, nans = nan_extend_edges_and_interpolate(xs[xsind], X)

        # do the transformation
        X = self.transformed(X, xs[xsind])

        # set NaNs where there were NaNs in the original array
        if nans is not None:
            X[nans] = np.nan

        # restore order
        return transform_back_to_features(xsind, mon, X)


def nan_extend_edges_and_interpolate(xs, X):
    """
    Handle NaNs at the edges are handled as with savgol_filter mode nearest:
    the edge values are interpolated. NaNs in the middle are interpolated
    so that they do not propagate.
    """
    nans = None
    if np.any(np.isnan(X)):
        nans = np.isnan(X)
        X = X.copy()
        fill_edges(X)
        X = interp1d_with_unknowns_numpy(xs, X, xs)
    return X, nans


def transform_to_sorted_features(data):
    xs = getx(data)
    xsind = np.argsort(xs)
    mon = is_increasing(xsind)
    X = data.X
    X = X if mon else X[:, xsind]
    return xs, xsind, mon, X


def transform_back_to_features(xsind, mon, X):
    return X if mon else X[:, np.argsort(xsind)]


def fill_edges(mat):
    """Replace (inplace!) NaN at sides with the closest value"""
    for l in mat:
        loc = np.where(~np.isnan(l))[0]
        if len(loc):
            fi, li = loc[[0, -1]]
            l[:fi] = l[fi]
            l[li + 1:] = l[li]


def remove_whole_nan_ys(x, ys):
    """Remove whole NaN columns of ys with corresponding x coordinates."""
    whole_nan_columns = np.isnan(ys).all(axis=0)
    if np.any(whole_nan_columns):
        x = x[~whole_nan_columns]
        ys = ys[:, ~whole_nan_columns]
    return x, ys


def interp1d_with_unknowns_numpy(x, ys, points, kind="linear"):
    if kind != "linear":
        raise NotImplementedError
    out = np.zeros((len(ys), len(points)))*np.nan
    sorti = np.argsort(x)
    x = x[sorti]
    for i, y in enumerate(ys):
        y = y[sorti]
        nan = np.isnan(y)
        xt = x[~nan]
        yt = y[~nan]
        # do not interpolate unknowns at the edges
        if len(xt):  # check if all values are removed
            out[i] = np.interp(points, xt, yt, left=np.nan, right=np.nan)
    return out


def interp1d_with_unknowns_scipy(x, ys, points, kind="linear"):
    out = np.zeros((len(ys), len(points)))*np.nan
    sorti = np.argsort(x)
    x = x[sorti]
    for i, y in enumerate(ys):
        y = y[sorti]
        nan = np.isnan(y)
        xt = x[~nan]
        yt = y[~nan]
        if len(xt):  # check if all values are removed
            out[i] = interp1d(xt, yt, fill_value=np.nan, assume_sorted=True,
                              bounds_error=False, kind=kind, copy=False)(points)
    return out


def interp1d_wo_unknowns_scipy(x, ys, points, kind="linear"):
    return interp1d(x, ys, fill_value=np.nan, kind=kind, bounds_error=False)(points)


def edge_baseline(x, y):
    i = np.array([0, -1])
    return interp1d(x[i], y[:, i], axis=1)(x) if len(x) else 0