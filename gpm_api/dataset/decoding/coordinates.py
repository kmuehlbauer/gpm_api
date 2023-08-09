#!/usr/bin/env python3
"""
Created on Fri Jul 28 13:50:05 2023

@author: ghiggi
"""
import functools
import os
import warnings

import numpy as np

from gpm_api.utils.warnings import GPM_Warning
from gpm_api.utils.yaml import read_yaml_file


def ensure_valid_coords(ds, raise_error=False):
    # invalid_coords = np.logical_or(ds["lon"].data == -9999.9,
    #                                ds["lat"].data == -9999.9)
    invalid_coords = np.logical_or(
        np.logical_or(ds["lon"].data < -180, ds["lon"].data > 180),
        np.logical_or(ds["lat"].data < -90, ds["lat"].data > 90),
    )
    if np.any(invalid_coords):
        # Raise error or add warning
        msg = "Invalid coordinate in the granule."
        if raise_error:
            raise ValueError(msg)
        else:
            warnings.warn(msg, GPM_Warning)

        da_invalid_coords = ds["lon"].copy()
        da_invalid_coords.data = invalid_coords
        # For each variable, set NaN value where invalid coordinates
        ds = ds.where(~da_invalid_coords)
        # Add NaN to longitude and latitude
        ds["lon"] = ds["lon"].where(~da_invalid_coords)
        ds["lat"] = ds["lat"].where(~da_invalid_coords)
    return ds


def _add_cmb_range_coordinate(ds, product, scan_mode):
    """Add range coordinate to 2B-<CMB> products."""
    if "range" in list(ds.dims):
        if scan_mode in ["NS", "KuKaGMI", "KuGMI", "KuTMI"]:
            range_values = np.arange(0, 88 * 250, step=250)
            ds = ds.assign_coords({"range": range_values})
    return ds


def _add_cmb_coordinates(ds, product, scan_mode):
    """Set coordinates of 2B-GPM-CORRA product."""
    if "pmw_frequency" in list(ds.dims):
        pmw_frequency = [
            "10V",
            "10H",
            "19V",
            "19H",
            "23V",
            "37V",
            "37H",
            "89V",
            "89H",
            "165V",
            "165H",
            "183V3",
            "183V7",
        ]
        ds = ds.assign_coords({"pmw_frequency": pmw_frequency})
    if scan_mode == "KuKaGMI" or scan_mode == "NS":
        if "radar_frequency" in list(ds.dims):
            ds = ds.assign_coords({"radar_frequency": ["Ku", "Ka"]})
    ds = _add_cmb_range_coordinate(ds, product, scan_mode)
    return ds


def _add_radar_range_coordinate(ds, product, scan_mode):
    """Add range coordinate to 2A-<RADAR> products."""
    # - V6 and V7: 1BKu 260 bins NS and MS, 130 at HS
    if "range" in list(ds.dims):
        if scan_mode in ["HS"]:
            range_values = np.arange(0, 88 * 250, step=250)
            ds = ds.assign_coords({"range": range_values})
        if scan_mode in ["FS", "MS", "NS"]:
            range_values = np.arange(0, 176 * 125, step=125)
            ds = ds.assign_coords({"range": range_values})
    return ds


def _add_wished_coordinates(ds):
    """Add wished coordinates to the dataset."""
    from gpm_api.dataset.groups_variables import WISHED_COORDS

    for var in WISHED_COORDS:
        if var in list(ds):
            ds = ds.set_coords(var)
    return ds


def _add_radar_coordinates(ds, product, scan_mode):
    """Add range, height, radar_frequency, paramDSD coordinates to <RADAR> products."""
    if product == "2A-DPR":
        if "radar_frequency" in list(ds.dims):
            ds = ds.assign_coords({"radar_frequency": ["Ku", "Ka"]})
    if product in ["2A-DPR", "2A-Ku", "2A-Ka", "2A-PR"]:
        if "paramDSD" in list(ds):
            ds = ds.assign_coords({"DSD_params": ["Nw", "Dm"]})
    # Add radar range
    ds = _add_radar_range_coordinate(ds, product, scan_mode)
    return ds


@functools.lru_cache(maxsize=None)
def get_pmw_frequency_dict():
    """Get PMW info dictionary."""
    from gpm_api import _root_path

    fpath = os.path.join(_root_path, "gpm_api", "etc", "pmw_frequency.yml")
    return read_yaml_file(fpath)


@functools.lru_cache(maxsize=None)
def get_pmw_frequency(sensor, scan_mode):
    """Get product info dictionary."""
    pmw_dict = get_pmw_frequency_dict()
    pmw_frequency = pmw_dict[sensor][scan_mode]
    return pmw_frequency


def _add_1c_pmw_frequency(ds, product, scan_mode):
    """Add the 'pmw_frequency' coordinates to 1C-<PMW> products."""
    if "pmw_frequency" in list(ds.dims):
        pmw_frequency = get_pmw_frequency(sensor=product.split("-")[1], scan_mode=scan_mode)
        ds = ds.assign_coords({"pmw_frequency": pmw_frequency})
    return ds


def _add_pmw_coordinates(ds, product, scan_mode):
    """Add coordinates to PMW products."""
    if product.startswith("1C"):
        ds = _add_1c_pmw_frequency(ds, product, scan_mode)
    return ds


def set_coordinates(ds, product, scan_mode):
    # Ensure valid coordinates
    if "cross_track" in list(ds.dims):
        ds = ensure_valid_coords(ds, raise_error=False)

    # Add range_id coordinate
    if "range" in list(ds.dims):
        range_id = np.arange(ds.dims["range"])
        ds = ds.assign_coords({"gpm_range_id": ("range", range_id)})

    # Add wished coordinates
    ds = _add_wished_coordinates(ds)

    #### Convert sunLocalTime to hourly timedelta
    if "sunLocalTime" in ds:
        ds["sunLocalTime"] = ds["sunLocalTime"] / 10**9 / 60 / 60

    #### PMW
    # - 1C products
    if product.startswith("1C"):
        ds = _add_pmw_coordinates(ds, product, scan_mode)

    #### RADAR
    if product in ["2A-DPR", "2A-Ku", "2A-Ka", "2A-PR"]:
        ds = _add_radar_coordinates(ds, product, scan_mode)

    #### CMB
    if product == ["2B-GPM-CORRA", "2B-TRMM-CORRA"]:
        ds = _add_cmb_coordinates(ds, product, scan_mode)

    #### SLH and CSH products
    if product in ["2A-GPM-SLH", "2B-GPM-CSH"] and "nlayer" in list(ds.dims):
        # Fixed heights for 2HSLH and 2HCSH
        # - FileSpec v7: p.2395, 2463
        height = np.linspace(0.25 / 2, 20 - 0.25 / 2, 80) * 1000  # in meters
        ds = ds.rename_dims({"nlayer": "height"})
        ds = ds.assign_coords({"height": height})
        ds["height"].attrs["units"] = "km a.s.l"
    return ds