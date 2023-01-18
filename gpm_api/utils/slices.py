#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 10 18:46:00 2022

@author: ghiggi
"""
import numpy as np
from functools import reduce

####---------------------------------------------------------------------------.
#### Tools for list_slices  


def get_list_slices_from_indices(indices):
    """Return a list of slices from a list/array of integer indices.

    Example:
        [0,1,2,4,5,8] --> [slices(0,3),slice(4,6), slice(8,9)]
    """
    # Checks
    if len(indices) == 0: 
        list_slices = []
    indices = np.asarray(indices).astype(int)
    indices = sorted(np.unique(indices))
    if np.any(np.sign(indices) < 0):
        raise ValueError("get_list_slices_from_indices expects only positive"
                         " integer indices.")
    if len(indices) == 1:
        return [slice(indices[0], indices[0] + 1)]
    # Retrieve slices
    # idx_splits = np.where(np.diff(indices) > 1)[0]
    # if len(idx_splits) == 0:
    #     list_slices = [slice(min(indices), max(indices))]
    # else:
    #     list_idx = np.split(indices, idx_splits+1)
    #     list_slices = [slice(x.min(), x.max()+1) for x in list_idx]
    start = indices[0]
    previous = indices[0]
    list_slices = []
    for idx in indices[1:]:
        if idx - previous == 1:
            previous = idx
        else:
            list_slices.append(slice(start, previous + 1))
            start = idx
            previous = idx
    list_slices.append(slice(start, previous + 1))
    return list_slices


def get_indices_from_list_slices(list_slices, check_non_intersecting=True):
    """Return a numpy array of indices from a list of slices."""
    if len(list_slices) == 0: 
        return np.array([])
    list_indices = [np.arange(slc.start, slc.stop, slc.step) for slc in list_slices]
    indices, counts = np.unique(np.concatenate(list_indices), return_counts=True)
    if check_non_intersecting and np.any(counts > 1):
        raise ValueError("The list of slices contains intersecting slices!")
    return indices


def list_slices_intersection(*args):
    """Return the intersecting slices from multiple list of slices."""
    list_indices = [get_indices_from_list_slices(l) for l in list(args)]
    intersect_indices = reduce(np.intersect1d, list_indices)
    return get_list_slices_from_indices(intersect_indices)


def list_slices_union(*args):
    """Return the union slices from multiple list of slices."""
    list_indices = [get_indices_from_list_slices(l) for l in list(args)]
    union_indices = np.unique(np.concatenate(list_indices))
    return get_list_slices_from_indices(union_indices)


def list_slices_combine(*args):
    """Combine together a list of list_slices, without any additional operation."""
    return [slc for list_slices in args for slc in list_slices]


def list_slices_simplify(list_slices):
    """Simplify list of of sequential slices.

    Example 1: [slice(0,2), slice(2,4)] --> [slice(0,4)]
    """
    if len(list_slices) <= 1:
        return list_slices
    indices = get_indices_from_list_slices(list_slices, check_non_intersecting=False)
    return get_list_slices_from_indices(indices)


def _list_slices_sort(list_slices):
    """Sort a single list of slices."""
    return sorted(list_slices, key=lambda x: x.start)


def list_slices_sort(*args):
    """Sort a single or multiple list of slices by slice.start.
    
    It output a single list of slices!
    """
    list_slices = list_slices_combine(*args)
    list_slices = _list_slices_sort(list_slices)
    return list_slices


# TODO: RENAME list_slices_filter
def filter_slices_by_size(list_slices, min_size=None, max_size=None):
    """Filter list of slices by size."""
    if min_size is None and max_size is None:
        return list_slices
    # Define min and max size if one is not specified
    min_size = 0 if min_size is None else min_size
    max_size = np.inf if max_size is None else max_size
    # Get list of slice sizes
    sizes = [
        get_slice_size(slc) if isinstance(slc, slice) else 0 for slc in list_slices
    ]
    # Retrieve valid slices
    valid_bool = np.logical_and(
        np.array(sizes) >= min_size, np.array(sizes) <= max_size
    )
    list_slices = np.array(list_slices)[valid_bool].tolist()
    return list_slices


# TODO: RENAME get_list_slices_from_bool_arr
def get_contiguous_true_slices(
    bool_arr, include_false=True, skip_consecutive_false=True
):
    """Return the slices corresponding to sequences of True in the input arrays.

    If include_false=True, the last element of each slice sequence (except the last) will be False
    If include_false=False, no element in each slice sequence will be False
    If skip_consecutive_false=True (default), the first element of each slice must be a True.
    If skip_consecutive_false=False, it returns also slices of size 1 which selects just the False value.
    Note: if include_false = False, skip_consecutive_false is automatically True.
    """
    # Check the arguments
    if not include_false:
        skip_consecutive_false = True

    # If all True
    if np.all(bool_arr):
        list_slices = [slice(0, len(bool_arr))]
    # If all False
    elif np.all(~bool_arr):
        if skip_consecutive_false:
            list_slices = []
        else:
            list_slices = [slice(i, i + 1) for i in range(0, len(bool_arr))]
    # If True and False
    else:
        # Retrieve indices where False start to occur
        false_indices = np.argwhere(~bool_arr).flatten()
        # Prepend -1 so first start start at 0, if no False at idx 0
        false_indices = np.append(-1, false_indices)
        list_slices = []
        for i in range(1, len(false_indices)):
            idx_before = false_indices[i - 1]
            idx = false_indices[i]
            if skip_consecutive_false:
                if idx - idx_before == 1:
                    continue
            # Define start
            start = idx_before + 1
            # Define stop
            if include_false:
                stop = idx + 1
            else:
                stop = idx
            # Define slice
            slc = slice(start, stop)
            list_slices.append(slc)

        # Includes the last slice (if the last bool_arr element is not False)
        if idx < len(bool_arr) - 1:
            start = idx + 1
            stop = len(bool_arr)
            slc = slice(start, stop)
            list_slices.append(slc)

    # Return list of slices
    return list_slices

# tests for _get_contiguous_true_slices
# bool_arr = np.array([True, False, True, True, True])
# bool_arr = np.array([True, True, True, False, True])
# bool_arr = np.array([True, True, True, True, False])
# bool_arr = np.array([True, False, False, True, True])
# bool_arr = np.array([True, True, True, False, False])
# bool_arr = np.array([False, True, True, True, False])
# bool_arr = np.array([False, False, True, True, True])
# bool_arr = np.array([False])


####----------------------------------------------------------------------------.
#### Tools for slice manipulation

def ensure_is_slice(slc):
    if isinstance(slc, slice):
        return slc
    else:
        if isinstance(slc, int):
            slc = slice(slc, slc + 1)
        elif isinstance(slc, (list, tuple)) and len(slc) == 1:
            slc = slice(slc[0], slc[0] + 1)
        elif isinstance(slc, np.ndarray) and slc.size == 1:
            slc = slice(slc.item(), slc.item() + 1)
        else:
            # TODO: check if continuous
            raise ValueError("Impossibile to convert to a slice object.")
    return slc


def get_slice_size(slc):
    """Get size of the slice.
    
    Note: The actual slice size must not be representative of the true slice if 
    slice.stop is larger than the length of object to be sliced.
    """
    if not isinstance(slc, slice):
        raise TypeError("Expecting slice object")
    size = slc.stop - slc.start
    return size


def get_idx_bounds_from_slice(slc):
    """Get start and end indices of the slice.
    
    Note: For index based selection, use idx_start:idx_end+1 !
    """    
    if not isinstance(slc, slice):
        raise TypeError("Expecting slice object")
    idx_start = slice.start
    idx_end = slice.stop - 1
    return idx_start, idx_end


def get_slice_from_idx_bounds(idx_start, idx_end):
    """Return the slice required to include the idx bounds."""
    return slice(idx_start, idx_end+1)
   

def pad_slice(slc, padding, min_start=0, max_stop=np.inf): 
    """
    Increase/decrease the slice with the padding argument.
    
    Parameters
    ----------
    slc : slice
        Slice objects.
    padding : int
        Padding to be applied to the slice.
    min_start : int, optional
       The default is np.inf.
       The minimum value for the start of the new slice.
       The default is 0.
    max_stop : int
        The maximum value for the stop of the new slice.

    Returns
    -------
    list_slices : TYPE
        The list of slices after applying padding.
    """
    
    new_slice = slice(max(slc.start - padding, 0), min(slc.stop + padding, max_stop))
    return new_slice


def pad_slices(list_slices, padding, valid_shape):
    """
    Increase/decrease the list of slices with the padding argument.
    
    Parameters
    ----------
    list_slices : list
        List of slice objects.
    padding : (int or tuple)
        Padding to be applied on each slice.
    valid_shape : tuple
        The shape of the array which the slices should be valid on. 

    Returns
    -------
    list_slices : TYPE
        The list of slices after applying padding.
    """
    # Check the inputs 
    if isinstance(padding, int):
        padding = [padding] * len(list_slices)
    if isinstance(valid_shape, int):
        valid_shape = [valid_shape] * len(list_slices)
    if isinstance(padding, (list, tuple)) and len(padding) != len(valid_shape):
        raise ValueError("Invalid padding. The length of padding should be the same as the length of valid_shape.")
    # Apply padding 
    list_slices = [pad_slice(s, padding=p, min_start=0, max_stop=valid_shape[i]) for i, (s, p) in enumerate(zip(list_slices, padding))]
    return list_slices


# min_size = 10
# min_start = 0
# max_stop = 20 
# slc = slice(1, 5)   # left bound
# slc = slice(15, 20) # right bound
# slc = slice(8, 12) # middle

def enlarge_slice(slc, min_size, min_start=0, max_stop=np.inf):
     """
     Enlarge a slice object to have at least a size of min_size. 
     
     The function enforces the left and right bounds of the slice by max_stop and min_start.
     If the original slice size is larger than min_size, the original slice will be returned.
                 
     Parameters
     ----------
     slc : slice
         The original slice object to be enlarged.
     min_size : min_size
         The desired minimum size of the new slice.
     min_start : int, optional
        The default is np.inf.
        The minimum value for the start of the new slice.
        The default is 0.
     max_stop : int
         The maximum value for the stop of the new slice.

     Returns
     -------
     slice
         The new slice object with a size of at least min_size and respecting the left and right bounds.

     """
     # Get slice size 
     slice_size = get_slice_size(slc)
     
     # If slice size larger than min_size, return the slice 
     if slice_size >= min_size:
         return slc
          
     # Calculate the number of points to add on both sides
     n_indices_to_add = min_size - slice_size
     add_to_left = add_to_right = n_indices_to_add // 2
     
     # If n_indices_to_add is odd, add + 1 on the left 
     if n_indices_to_add % 2 == 1:
         add_to_left += 1
     
     # Adjust adding for left and right bounds 
     naive_start = slc.start - add_to_left 
     naive_stop = slc.stop + add_to_right
     if naive_start <= min_start:
         exceeding_left_size = min_start - naive_start
         add_to_right += exceeding_left_size
         add_to_left -= exceeding_left_size
     if naive_stop >= max_stop:
         exceeding_right_size = naive_stop - max_stop
         add_to_right -= exceeding_right_size
         add_to_left += exceeding_right_size
     
     # Define new slice 
     start = slc.start - add_to_left
     stop = slc.stop + add_to_right
     new_slice = slice(start, stop) 
     
     # Check 
     assert  get_slice_size(new_slice) == min_size
     
     # Return new slice 
     return new_slice
 

def enlarge_slices(list_slices, min_size, valid_shape):
    """
    Enlarge a list of slice object to have at least a size of min_size. 
     
    The function enforces the left and right bounds of the slice to be between 0 and valid_shape.
    If the original slice size is larger than min_size, the original slice will be returned.
    
    Parameters
    ----------
    list_slices : list
        List of slice objects.
    min_size : (int or tuple)
        Minimum size of the output slice.
    valid_shape : tuple
        The shape of the array which the slices should be valid on. 

    Returns
    -------
    list_slices : list
        The list of slices after enlarging it (if necessary).
    """
    # Check the inputs 
    if isinstance(min_size, int):
        min_size = [min_size] * len(list_slices)
    if isinstance(valid_shape, int):
        valid_shape = [valid_shape] * len(list_slices)
    if isinstance(min_size, (list, tuple)) and len(min_size) != len(min_size):
        raise ValueError("Invalid min_size. The length of min_size should be the same as the length of valid_shape.")
    # Enlarge the slice  
    list_slices = [enlarge_slice(slc, min_size=s, min_start=0, max_stop=valid_shape[i]) for i, (slc, s) in enumerate(zip(list_slices, min_size))]
    return list_slices

###----------------------------------------------------------------------------.
 







