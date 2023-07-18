#!/usr/bin/env python3
"""
Created on Tue Jul 18 17:07:22 2023

@author: ghiggi
"""
import warnings

import numpy as np
import xarray as xr

from gpm_api.dataset.attrs import get_granule_attrs
from gpm_api.dataset.conventions import finalize_dataset
from gpm_api.dataset.coords import get_coords
from gpm_api.dataset.decoding import apply_custom_decoding
from gpm_api.dataset.groups_variables import _get_relevant_groups_variables
from gpm_api.io.checks import (
    check_groups,
    check_scan_mode,
    check_variables,
)
from gpm_api.io.info import get_product_from_filepath, get_version_from_filepath
from gpm_api.utils.checks import is_regular
from gpm_api.utils.time import ensure_time_validity
from gpm_api.utils.warnings import GPM_Warning


def _prefix_dataset_group_variables(ds, group):
    """Prefix group dataset variables."""
    var_dict = {var: group + "/" + var for var in ds.data_vars}
    ds = ds.rename_vars(var_dict)
    return ds


def _remove_dummy_variables(ds):
    """Return dummy variables from HDF dataset group."""
    dummy_variables = [
        "Latitude",
        "Longitude",
        # IMERG bnds
        "time_bnds",
        "lat_bnds",
        "lon_bnds",
    ]
    dummy_variables = np.array(dummy_variables)
    variables_to_drop = dummy_variables[np.isin(dummy_variables, list(ds.data_vars))]
    ds = ds.drop_vars(variables_to_drop)
    return ds


def _subset_dataset_variables(ds, variables):
    """Selectr xr.Dataset variables included in the variables list.

    'variables' can contain variables not present in the xr.Dataset.
    If variables=None, does not subset the xr.Dataset.
    """
    if variables is not None:
        variables_subset = np.array(variables)[np.isin(variables, list(ds.data_vars))].tolist()
        ds = ds[variables_subset]
    return ds


def _process_group_dataset(ds, group, variables, prefix_group=False):
    """Subset group dataset and change variable names if asked."""
    ds = _subset_dataset_variables(ds, variables)
    ds = _remove_dummy_variables(ds)
    if prefix_group:
        ds = _prefix_dataset_group_variables(ds, group)
    return ds


def _get_scan_mode_info(dt, scan_mode, variables, groups):
    """Retrieve coordinates, attributes and valid variables and groups."""
    # Get global attributes from the root
    attrs = get_granule_attrs(dt)
    attrs["ScanMode"] = scan_mode

    # Get coordinates
    coords = get_coords(dt, scan_mode)

    # Get groups to process (filtering out groups without any `variables`)
    groups, variables = _get_relevant_groups_variables(
        dt, scan_mode=scan_mode, variables=variables, groups=groups
    )
    return (coords, attrs, groups, variables)


def _get_flattened_scan_mode_dataset(dt, scan_mode, groups, variables=None, prefix_group=False):
    """Retrieve scan mode dataset."""
    list_ds = []
    for group in groups:
        if group == scan_mode:
            ds = dt[scan_mode].to_dataset()
            group = ""
        else:
            ds = dt[scan_mode][group].to_dataset()
        ds = _process_group_dataset(ds, group, variables, prefix_group=False)
        list_ds.append(ds)
    ds = xr.merge(list_ds)
    return ds


def _get_scan_mode_dataset(
    filepath,
    scan_mode,
    variables=None,
    groups=None,
    prefix_group=False,
    chunks={},
    decode_cf=False,
):
    """Retrieve scan mode xr.Dataset."""
    from gpm_api.dataset.datatree import _open_datatree

    dt = _open_datatree(
        filepath=filepath, chunks=chunks, decode_cf=decode_cf, use_api_defaults=True
    )

    # Retrieve granule info
    coords, attrs, groups, variables = _get_scan_mode_info(
        dt=dt, scan_mode=scan_mode, variables=variables, groups=groups
    )

    # Create flattened dataset for a specific scan_mode
    ds = _get_flattened_scan_mode_dataset(
        dt, scan_mode=scan_mode, groups=groups, variables=variables, prefix_group=prefix_group
    )

    # Assign coords
    # - Silence warning related to datetime precision
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ds = ds.assign_coords(coords)
    # Assign global attributes
    ds.attrs = attrs
    return ds


def get_variables_dims(ds):
    """Retrieve the dimensions used by the xr.Dataset variables."""
    dims = np.unique(np.concatenate([list(ds[var].dims) for var in ds.data_vars]))
    return dims


def unused_var_dims(ds):
    """Retrieve the dimensions not used by the the xr.Dataset variables."""
    var_dims = set(get_variables_dims(ds))
    ds_dims = set(list(ds.dims))
    unused_dims = ds_dims.difference(var_dims)
    return list(unused_dims)


def remove_unused_var_dims(ds):
    """Remove coordinates and dimensions not used by the xr.Dataset variables."""
    unused_dims = unused_var_dims(ds)
    return ds.drop_dims(unused_dims)


def _open_granule(
    filepath,
    scan_mode=None,
    groups=None,
    variables=None,
    decode_cf=False,
    chunks="auto",
    prefix_group=True,
):
    """Open granule file into xarray Dataset."""
    # Get product and version
    product = get_product_from_filepath(filepath)
    version = get_version_from_filepath(filepath)

    # Check variables and groups
    variables = check_variables(variables)
    groups = check_groups(groups)

    # Check scan_mode
    scan_mode = check_scan_mode(scan_mode, product, version)

    # Retrieve the granule dataset (without cf decoding)
    ds = _get_scan_mode_dataset(
        filepath=filepath,
        scan_mode=scan_mode,
        groups=groups,
        variables=variables,
        prefix_group=prefix_group,
        chunks=chunks,
        decode_cf=False,
    )

    ###-----------------------------------------------------------------------.
    ### Clean attributes, decode variables
    # Apply custom processing
    ds = apply_custom_decoding(ds, product)

    # Remove coords and dimensions not exploited by data variables
    ds = remove_unused_var_dims(ds)

    ###-----------------------------------------------------------------------.
    ## Check swath time coordinate
    # Ensure validity of the time dimension
    # - Infill up to 10 consecutive NaT
    # - Do not check for regular time dimension !
    # --> TODO: this can be moved into get_orbit_coords !
    ds = ensure_time_validity(ds, limit=10)

    # Try to warn if non-contiguous scans are present in a GPM Orbit
    # - If any of the  GPM Orbit specified variables has the cross-track dimension, the check raise an error
    # - If ds is a GPM Grid Granule, is always a single timestep so always True
    try:
        if not is_regular(ds):
            msg = f"The GPM granule {filepath} has non-contiguous scans !"
            warnings.warn(msg, GPM_Warning)
    except Exception:
        pass

    ###-----------------------------------------------------------------------.
    ## Check geolocation latitude/longitude coordinates
    # TODO: check_valid_geolocation
    # TODO: ensure_valid_geolocation (1 spurious pixel)
    # TODO: ds_gpm.gpm_api.valid_geolocation

    ###-----------------------------------------------------------------------.
    # Return xr.Dataset
    return ds


def open_granule(
    filepath,
    scan_mode=None,
    groups=None,
    variables=None,
    decode_cf=False,
    chunks={},
    prefix_group=True,
    use_gpm_api_defaults=True,
):
    """
    Create a lazy xarray.Dataset with relevant GPM data and attributes
    for a specific granule.

    Parameters
    ----------
    fpath : str
        Filepath of GPM granule dataset
    scan_mode : str
        The radar products have the following scan modes
        - 'FS' = Full Scan --> For Ku, Ka and DPR      (since version 7 products)
        - 'NS' = Normal Scan --> For Ku band and DPR   (till version 6  products)
        - 'MS' = Matched Scans --> For Ka band and DPR  (till version 6 for L2 products)
        - 'HS' = High-sensitivity Scans --> For Ka band and DPR
        For version 7:
        - For products '1B-Ku', '2A-Ku' and '2A-ENV-Ku', specify 'FS'
        - For products '1B-Ka' specify either 'MS' or 'HS'.
        - For products '2A-Ka' and '2A-ENV-Ka' specify 'FS' or 'HS'.
        - For products '2A-DPR' and '2A-ENV-DPR' specify either 'FS' or 'HS'
        For version < 7:
        - NS must be used instead of FS in Ku product.
        - MS is available in DPR L2 products till version 6.

        For product '2A-SLH', specify scan_mode = 'Swath'
        For product '2A-<PMW>', specify scan_mode = 'S1'
        For product '2B-GPM-CSH', specify scan_mode = 'Swath'.
        For product '2B-GPM-CORRA', specify either 'KuKaGMI' or 'KuGMI'.
        For product 'IMERG-ER','IMERG-LR' and 'IMERG-FR', specify scan_mode = 'Grid'.

        The above guidelines related to product version 7.

    variables : list, str
         Datasets names to extract from the HDF5 file.
    groups
        Groups to extract from the HDF5 file.
    chunks : str, list, optional
        Chunk size for dask array. The default is '{}'.
        If you want to load data in memory directly, specify chunks=None.

        Hint: xarray’s lazy loading of remote or on-disk datasets is often but not always desirable.
        Before performing computationally intense operations, load the Dataset
        entirely into memory by invoking ds.compute().

        Custom chunks can be specified by: TODO
        - Provide a list (with length equal to 'variables') specifying
          the chunk size option for each variable.
    decode_cf: bool, optional
        Whether to decode the dataset. The default is False.
    prefix_group: bool, optional
        Whether to add the group as a prefix to the variable names.
        THe default is True.

    Returns
    -------

    ds:  xarray.Dataset

    """
    # Open granule
    ds = _open_granule(
        filepath=filepath,
        scan_mode=scan_mode,
        groups=groups,
        variables=variables,
        decode_cf=decode_cf,
        chunks=chunks,
        prefix_group=prefix_group,
    )

    # Finalize granule
    product = get_product_from_filepath(filepath)
    ds = finalize_dataset(
        ds=ds, product=product, decode_cf=decode_cf, start_time=None, end_time=None
    )
    return ds