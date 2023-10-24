#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 20 14:33:33 2023

@author: ghiggi
"""
import os
import xarray as xr
import pytest
from gpm_api.dataset.granule import open_granule
from gpm_api import _root_path
import glob
import gpm_api


PRODUCT_TYPES = ["RS"]


gpm_api.config.set(
    {
        "warn_non_contiguous_scans": False,
        "warn_non_regular_timesteps": False,
        "warn_invalid_spatial_coordinates": False,
    }
)


def test_open_granule_on_real_files(tmp_path):
    """Test open_granule on real files.

    Load cut granules and check that the new file is identical to the saved reference.

    Run `python gpm_api/tests/test_dataset/generate_test_granule_data.py` to generate the test granules.
    The expected granules directory structure is:

    tests/data/granules
    ├── cut
    │   ├── V7/RS/1A-GMI
    │   │   └── 1A.GPM.GMI.COUNT2021.20140304-S223658-E000925.000082.V07A.HDF5
    ├── processed
    │   ├── V7/RS/1A-GMI
    │       ├── S1.nc
    │       ├── S2.nc
    │       ├── S4.nc
    │       └── S5.nc
    └── ...
    """

    granules_dir_path = os.path.join(_root_path, "gpm_api", "tests", "data", "granules")
    granules_dir_path = os.path.join("/home/ghiggi/GPM_TEST_DATA_DEMO")

    if not os.path.exists(granules_dir_path):
        pytest.skip("Test granules not found. Please run `python generate_test_granule_data.py`.")

    cut_dir_path = os.path.join(granules_dir_path, "cut")

    for product_type in PRODUCT_TYPES:
        if product_type == "RS":
            cut_filepaths = glob.glob(os.path.join(cut_dir_path, "RS", "*", "*", "*"))
        else:
            cut_filepaths = glob.glob(os.path.join(cut_dir_path, "NRT", "*", "*"))

        if len(cut_filepaths) == 0:
            raise ValueError("No test data found.")

        for cut_filepath in cut_filepaths:
            print(cut_filepath)
            processed_dir = os.path.dirname(cut_filepath.replace("cut", "processed"))
            processed_filenames = os.listdir(processed_dir)
            processed_filepaths = [
                os.path.join(processed_dir, filename) for filename in processed_filenames
            ]
            scan_modes = [os.path.splitext(filename)[0] for filename in processed_filenames]
            for scan_mode, processed_filepath in zip(scan_modes, processed_filepaths):
                ds = open_granule(cut_filepath, scan_mode=scan_mode).compute()
                ds_expected = xr.open_dataset(processed_filepath).compute()

                # Remove history attribute
                _ = ds.attrs.pop("history", None)
                _ = ds_expected.attrs.pop("history", None)

                # Write dataset to disk
                # - This enable to apply array encodings
                # - This enable to apply custom netcdf attrs serialization
                # --> flag_values [0,1,2] --> [0 1 2]
                tmp_filepath = "/tmp/dummy.nc"  # TODO generalize for CI
                ds.to_netcdf(tmp_filepath)

                # Open encoded dataset
                ds = xr.open_dataset(tmp_filepath).compute()

                # Check equality
                xr.testing.assert_identical(ds, ds_expected)

                ####-----------------------------------------------------------.
                #### TO DEBUG
                # import numpy as np

                # # Remove attrs
                # ds.attrs = {}
                # ds_expected.attrs = {}

                # # Check equality
                # try:
                #     xr.testing.assert_identical(ds, ds_expected)
                # except Exception as e:
                #     print("ERROR")

                # var = "rainType2ADPR"
                # np.testing.assert_allclose(ds[var].data, ds_expected[var].data)
                # xr.testing.assert_identical( ds[var], ds_expected[var])

                # ds[var] == ds_expected[var]

                # ds["lat"] - ds_expected["lat"]
                # ds["nearSurfacePrecipRate"].data - ds_expected["nearSurfacePrecipRate"].data

                # # cut_filepath = "/home/ghiggi/GPM_TEST_DATA_DEMO/cut/RS/V7/2A-GPM-SLH/2A.GPM.DPR.GPM-SLH.20140308-S220950-E234217.000144.V06B.HDF5"
                # # rainType2ADPR
