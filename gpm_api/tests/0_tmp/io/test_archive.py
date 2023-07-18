#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 19 16:19:22 2023

@author: ghiggi
"""
import datetime
from gpm_api.configs import get_gpm_base_dir
from gpm_api.utils.archive import (
    check_archive_completeness,
    check_file_integrity,
    check_no_duplicated_files,
)

base_dir = get_gpm_base_dir()
product_type = "RS"
product = "2A-DPR"
version = 7
start_time = datetime.datetime(2022, 2, 1)
end_time = datetime.datetime(2022, 3, 1)
download = True
username = None
transfer_tool = "wget"
n_threads = 4
verbose = True

check_no_duplicated_files(
    base_dir=base_dir,
    product=product,
    start_time=start_time,
    end_time=end_time,
    version=version,
    product_type=product_type,
    verbose=True,
)

check_file_integrity(
    base_dir=base_dir,
    product=product,
    start_time=start_time,
    end_time=end_time,
    version=version,
    product_type=product_type,
    remove_corrupted=True,
    verbose=True,
)

check_archive_completeness(
    base_dir=base_dir,
    product=product,
    start_time=start_time,
    end_time=end_time,
    version=version,
    product_type=product_type,
    download=True,
    username="gionata.ghiggi@epfl.ch",
    transfer_tool=transfer_tool,
    n_threads=n_threads,
    verbose=verbose,
)

# TODO: SIMPLIFY periods by unique dates?
# --> call download_daily_data instead in check_archive_completeness
list_missing_periods = [
    ([datetime.datetime(2022, 2, 2, 22, 17, 44)], [datetime.datetime(2022, 2, 23, 1, 5, 7)]),
    ([datetime.datetime(2022, 2, 26, 7, 45, 58)], [datetime.datetime(2022, 2, 26, 9, 18, 33)]),
    ([datetime.datetime(2022, 2, 26, 20, 6, 31)], [datetime.datetime(2022, 2, 27, 0, 44, 15)]),
]