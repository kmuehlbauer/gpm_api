# -----------------------------------------------------------------------------.
# MIT License

# Copyright (c) 2024 GPM-API developers
#
# This file is part of GPM-API.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# -----------------------------------------------------------------------------.
"""This module tests quadmesh computations."""
import dask
import dask.array as da
import numpy as np
import pytest

from gpm.utils.area import (
    _from_bounds_to_corners,
    _from_corners_to_bounds,
    # _do_transform,
    geocentric_to_geographic,
    geographic_to_geocentric,
    get_centroids_from_corners,
    get_corners_from_centroids,
    get_corners_from_quadmesh,
    get_lonlat_corners_from_centroids,
    get_lonlat_quadmesh_vertices,
    get_projection_corners_from_1d_centroids,
    get_projection_corners_from_centroids,
    get_projection_quadmesh_vertices,
    # _get_numpy_quadmesh,
    # _get_dask_quadmesh,
    get_quadmesh_from_corners,
    # _infer_interval_breaks_numpy,
    # _infer_interval_breaks_dask,
    infer_interval_breaks,
    is_clockwise,
)


# TODO: check with z = None or zeros ...
def test_geographic_to_geocentric():
    """Test conversion from geographic to geocentric coordinates."""
    lons = np.array([[0, 10]])
    lats = np.array([[0, 10]])

    # Check results with numpy
    x, y, z = geographic_to_geocentric(lons, lats)
    assert x.shape == y.shape == z.shape, "Shape mismatch among x, y, z"
    assert x.shape == (1, 2)
    np.testing.assert_allclose(x[0, 0], 6378137.0)
    np.testing.assert_allclose(y[0, 0], 0)
    np.testing.assert_allclose(z[0, 0], 0)

    # Check results with dask
    x_dask, y_dask, z_dask = geographic_to_geocentric(dask.array.asarray(lons), dask.array.asarray(lats))
    np.testing.assert_allclose(x, x_dask.compute())
    np.testing.assert_allclose(y, y_dask.compute())
    np.testing.assert_allclose(z, z_dask.compute())


def test_geocentric_to_geographic():
    """Test conversion from geocentric to geographic coordinates."""
    x = np.array([[6378137.0, 0]])
    y = np.array([[0, 6378137.0]])
    z = np.array([[0, 0]])

    # Check results with numpy
    lons, lats, z1 = geocentric_to_geographic(x, y, z)
    assert lons.shape == lats.shape == z1.shape, "Shape mismatch between lons and lats"
    np.testing.assert_allclose(lons, np.array([[0.0, 90.0]]))
    np.testing.assert_allclose(lats, np.array([[0.0, 0.0]]))
    np.testing.assert_allclose(z1, np.array([[0.0, 0.0]]))

    # Check results with dask
    lons_dask, lats_dask, z1_dask = geocentric_to_geographic(
        dask.array.asarray(x),
        dask.array.asarray(y),
        dask.array.asarray(z),
    )
    np.testing.assert_allclose(lons, lons_dask.compute())
    np.testing.assert_allclose(lats, lats_dask.compute())
    np.testing.assert_allclose(z1, z1_dask.compute())


def test_is_clockwise():
    vertices = np.array([[0.5, 3.5], [0.5, 4.5], [1.5, 4.5], [1.5, 3.5]])
    assert is_clockwise(vertices)
    assert not is_clockwise(vertices[::-1, :])


def test_infer_interval_breaks_numpy():
    """Test inferring interval breaks with numpy array."""
    coord = np.array([0, 10, 20])
    breaks = infer_interval_breaks(coord)
    assert breaks.shape == (4,), "Shape mismatch for interval breaks"
    np.testing.assert_allclose(breaks, np.array([-5.0, 5.0, 15.0, 25.0]))


def test_infer_interval_breaks_dask():
    """Test inferring interval breaks with dask array."""
    coord = da.from_array(np.array([0, 10, 20]), chunks=2)
    breaks = infer_interval_breaks(coord)
    assert breaks.shape == (4,), "Shape mismatch for interval breaks"
    np.testing.assert_allclose(breaks.compute(), np.array([-5.0, 5.0, 15.0, 25.0]))


def test_get_corners_from_centroids():
    """Test getting corners from 2D centroids arrays."""
    centroids = np.array([[0, 10], [10, 20]])
    # Check with numpy
    corners = get_corners_from_centroids(centroids)
    assert corners.shape == (3, 3), "Shape mismatch for corners from centroids"
    expected_corners = np.array([[-10.0, 0.0, 10.0], [0.0, 10.0, 20.0], [10.0, 20.0, 30.0]])
    np.testing.assert_allclose(corners, expected_corners)
    # Check with dask
    corners_dask = get_corners_from_centroids(da.from_array(centroids, chunks=1))
    np.testing.assert_allclose(corners, corners_dask.compute())


def test_get_centroids_from_corners():
    """Test getting centroids from 2D centroids arrays."""
    corners = np.array([[0, 10, 20], [10, 20, 30], [20, 30, 40]])
    # Check with numpy
    centroids = get_centroids_from_corners(corners)
    assert centroids.shape == (2, 2), "Shape mismatch for centroids from corners"
    expected_centroids = np.array([[10.0, 20.0], [20.0, 30.0]])
    np.testing.assert_allclose(centroids, expected_centroids)
    # Check with dask
    centroids_dask = get_centroids_from_corners(da.from_array(corners, chunks=1))
    np.testing.assert_allclose(centroids, centroids_dask.compute())


def test_from_corners_to_bounds():
    """Test conversion from cell corners to cell vertices."""
    corners = np.array([[0, 10, 20], [30, 40, 50], [60, 70, 80]])
    # Check counterclockwise order
    bounds = _from_corners_to_bounds(corners)  # order = counterclockwise
    assert bounds.shape == (2, 2, 4), "Shape mismatch for bounds from corners"
    np.testing.assert_allclose(bounds[0, 0], np.array([0, 30, 40, 10]))

    # Check clockwise order
    bounds = _from_corners_to_bounds(corners, order="clockwise")
    assert bounds.shape == (2, 2, 4), "Shape mismatch for bounds from corners"
    np.testing.assert_allclose(bounds[0, 0], np.array([0, 10, 40, 30]))

    # Check with dask
    bounds_dask = _from_corners_to_bounds(da.from_array(corners, chunks=2), order="clockwise")
    assert bounds_dask.shape == (2, 2, 4), "Shape mismatch for bounds from corners"
    np.testing.assert_allclose(bounds, bounds_dask)


def test_from_bounds_to_corners():
    """Test conversion from bounds to corners."""
    corners = np.array([[0, 10, 20], [30, 40, 50], [60, 70, 80]])
    # Check counterclockwise order
    bounds = _from_corners_to_bounds(corners)
    corners_res = _from_bounds_to_corners(bounds)
    np.testing.assert_allclose(corners, corners_res)

    # Check clockwise order
    bounds = _from_corners_to_bounds(corners, order="clockwise")
    corners_res = _from_bounds_to_corners(bounds, order="clockwise")
    np.testing.assert_allclose(corners, corners_res)

    # Check dask
    corners_dask = da.from_array(corners, chunks=2)
    bounds = _from_corners_to_bounds(corners_dask, order="clockwise")
    corners_res_dask = _from_bounds_to_corners(bounds, order="clockwise")
    np.testing.assert_allclose(corners, corners_res_dask.compute())

    # TODO: Chunks differ !
    # corners_res_dask.chunks
    # corners_dask.chunks


def test_get_quadmesh_from_corners():
    """Test getting quadmesh from corners."""
    x_corners = np.array([[0, 10], [-5, 5]])
    y_corners = np.array([[4, 3], [2, 1]])

    # Check numpy
    quadmesh = get_quadmesh_from_corners(x_corners, y_corners)  # default is counterclockwise
    assert quadmesh.shape == (1, 1, 4, 2), "Shape mismatch for quadmesh from corners"
    np.testing.assert_allclose(quadmesh[:, :, :, 0], np.array([[[0, -5, 5, 10]]]))
    np.testing.assert_allclose(quadmesh[:, :, :, 1], np.array([[[4, 2, 1, 3]]]))

    # Check clockwise ordered
    quadmesh = get_quadmesh_from_corners(x_corners, y_corners, order="clockwise")  # default is counterclockwise
    assert quadmesh.shape == (1, 1, 4, 2), "Shape mismatch for quadmesh from corners"
    np.testing.assert_allclose(quadmesh[:, :, :, 0], np.array([[[0, 10, 5, -5]]]))
    np.testing.assert_allclose(quadmesh[:, :, :, 1], np.array([[[4, 3, 1, 2]]]))

    # Check dask
    quadmesh_dask = get_quadmesh_from_corners(
        da.from_array(x_corners, chunks=2),
        da.from_array(y_corners, chunks=2),
        order="clockwise",
    )
    np.testing.assert_allclose(quadmesh, quadmesh_dask)


def test_get_corners_from_quadmesh():
    """Test getting corners from quadmesh."""
    # Test with minimum shape (2x2) ... corresponding to single cell
    # --> y corners ordered upward (so no need of reordering vertices !)
    x_corners = np.array([[0, 10], [-5, 5]])
    y_corners = np.array([[4, 3], [2, 1]])
    # Check numpy
    quadmesh = get_quadmesh_from_corners(x_corners, y_corners)
    x_corners_res, y_corners_res = get_corners_from_quadmesh(quadmesh)
    np.testing.assert_allclose(x_corners_res, x_corners)
    np.testing.assert_allclose(y_corners_res, y_corners)
    # Check dask
    quadmesh_dask = get_quadmesh_from_corners(
        da.from_array(x_corners, chunks=2),
        da.from_array(y_corners, chunks=2),
    )
    x_corners_dask_res, y_corners_dask_res = get_corners_from_quadmesh(quadmesh_dask)
    np.testing.assert_allclose(x_corners, x_corners_dask_res.compute())
    np.testing.assert_allclose(y_corners, y_corners_dask_res.compute())


def test_get_lonlat_corners_from_centroids():
    """Test getting lon/lat corners from centroids."""
    lons = np.array([[0, 10], [20, 30]])
    lats = np.array([[10, 15], [0, 5]])
    lon_corners, lat_corners = get_lonlat_corners_from_centroids(lons, lats)
    assert lon_corners.shape == lat_corners.shape, "Shape mismatch between lon and lat corners"
    expected_lon_corners = np.array(
        [
            [-14.27407497, -4.80531025, 5.16026436],
            [5.19757839, 15.08698583, 25.20197428],
            [24.37604115, 34.12946232, 43.835406],
        ],
    )
    expected_lat_corners = np.array(
        [
            [11.79157893, 16.74949943, 21.2573865],
            [2.51977904, 7.6452206, 12.53485936],
            [-7.03008533, -2.33548415, 2.43539233],
        ],
    )
    np.testing.assert_allclose(lon_corners, expected_lon_corners)
    np.testing.assert_allclose(lat_corners, expected_lat_corners)


def test_get_lonlat_corners_from_nadir_swath():
    """Test getting lon/lat corners from centroids."""
    lons = np.array([[0, 10, 20, 30]])  # (1, 4)
    lats = np.array([[0, 0, 0, 0]])  # squeeze make it 1D # TODO: do not change shape !
    lon_corners, lat_corners = get_lonlat_corners_from_centroids(lons, lats)
    assert lon_corners.shape == (5, 2)
    assert lon_corners.shape == lat_corners.shape, "Shape mismatch between lon and lat corners"
    expected_lon_corners = np.array([[-5.0, -5.0], [5.0, 5.0], [15.0, 15.0], [25.0, 25.0], [35.0, 35.0]])
    expected_lat_corners = np.array(
        [
            [-5.03356764, 5.03356764],
            [-5.03356764, 5.03356764],
            [-5.03356764, 5.03356764],
            [-5.03356764, 5.03356764],
            [-5.03356764, 5.03356764],
        ],
    )
    np.testing.assert_allclose(lon_corners, expected_lon_corners)
    np.testing.assert_allclose(lat_corners, expected_lat_corners)


def test_get_lonlat_quadmesh_vertices():
    """Test getting lon/lat quadmesh vertices."""
    # Create centroids of shape (2x2)
    lons = np.array([[0, 10], [20, 30]])
    lats = np.array([[10, 15], [0, 5]])  # ordered upward

    # Get quadmesh vertices (counterclockwise)
    quadmesh_vertices = get_lonlat_quadmesh_vertices(lons, lats)  #  order="counterclockwise"
    assert quadmesh_vertices.shape == (2, 2, 4, 2), "Shape mismatch for quadmesh vertices"
    np.testing.assert_allclose(
        quadmesh_vertices[0, 0, :, 0],
        np.array([-14.27407, 5.1975, 15.0869, -4.8053]),
        atol=1e-4,
    )
    np.testing.assert_allclose(quadmesh_vertices[0, 0, :, 1], np.array([11.7915, 2.5197, 7.6452, 16.7494]), atol=1e-4)

    # Get quadmesh vertices (clockwise)
    quadmesh_vertices = get_lonlat_quadmesh_vertices(lons, lats, order="clockwise")
    assert quadmesh_vertices.shape == (2, 2, 4, 2), "Shape mismatch for quadmesh vertices"
    np.testing.assert_allclose(
        quadmesh_vertices[0, 0, :, 0],
        np.array([-14.27407, -4.8053, 15.0869, 5.1975]),
        atol=1e-4,
    )
    np.testing.assert_allclose(quadmesh_vertices[0, 0, :, 1], np.array([11.7915, 16.74949, 7.6452, 2.5197]), atol=1e-4)


def test_get_lonlat_quadmesh_vertices_at_antimeridian():
    """Test getting lon/lat quadmesh vertices."""
    # Create centroids of shape (2x2)
    lons = np.array([[-175.0, 175.0], [-175.0, 175.0]])
    lats = np.array([[10.0, 10.0], [-10.0, -10.0]])

    quadmesh_vertices = get_lonlat_quadmesh_vertices(lons, lats, order="counterclockwise")
    assert quadmesh_vertices.shape == (2, 2, 4, 2), "Shape mismatch for quadmesh vertices"

    # TODO: not implemented yet special case for antimeridian !
    # np.testing.assert_allclose(quadmesh_vertices[0, 0, :, 0], np.array([-170.07501496, -170.07501496, 180.0, 180.0]))
    # np.testing.assert_allclose(quadmesh_vertices[0, 0, :, 1], np.array([19.21762561, 0.0, 0.0, 19.48929974]))


def test_get_projection_corners_from_centroids():
    """Test getting projection corners from 2D centroids arrays."""
    x = np.array([[0, 10], [10, 20]])
    y = np.array([[0, 10], [10, 20]])
    x_corners, y_corners = get_projection_corners_from_centroids(x, y)
    assert x_corners.shape == y_corners.shape, "Shape mismatch between x and y corners"
    expected_x_corners = np.array([[-10.0, 0.0, 10.0], [0.0, 10.0, 20.0], [10.0, 20.0, 30.0]])
    expected_y_corners = np.array([[-10.0, 0.0, 10.0], [0.0, 10.0, 20.0], [10.0, 20.0, 30.0]])
    np.testing.assert_allclose(x_corners, expected_x_corners)
    np.testing.assert_allclose(y_corners, expected_y_corners)

    # Invalid inputs
    x = np.array([])
    y = np.array([1, 2])
    with pytest.raises(ValueError):
        get_projection_corners_from_centroids(x, y)

    # Single cell
    x = np.array([[0]])
    y = np.array([[0]])
    with pytest.raises(ValueError):
        get_projection_corners_from_centroids(x, y)

    # Different dimensions
    x = np.array([[0, 10], [10, 20]])
    y = np.array([1, 2])
    with pytest.raises(NotImplementedError):
        get_projection_corners_from_centroids(x, y)

    # Different shape
    x = np.array([[0, 10, 20], [10, 20, 30]])
    y = np.array([[0, 10], [10, 20]])
    with pytest.raises(ValueError):
        get_projection_corners_from_centroids(x, y)

    # Different input types
    x = np.array([[0, 10], [10, 20]])
    y = dask.array.from_array(np.array([[0, 10], [10, 20]]))
    with pytest.raises(TypeError):
        get_projection_corners_from_centroids(x, y)


def test_get_projection_corners_from_1d_centroids():
    """Test getting corners from 1D centroids."""
    # Case with both dimension of size > 1
    x = np.array([0, 10, 20])
    y = np.array([0, 10])
    x_corners, y_corners = get_projection_corners_from_1d_centroids(x, y)
    assert x_corners.shape == (3, 4), "Incorrect shape of corners"
    assert x_corners.shape == y_corners.shape, "Shape mismatch between x and y corners"
    expected_x_corners = np.array([[-5.0, 5.0, 15.0, 25.0], [-5.0, 5.0, 15.0, 25.0], [-5.0, 5.0, 15.0, 25.0]])
    expected_y_corners = np.array([[15.0, 15.0, 15.0, 15.0], [5.0, 5.0, 5.0, 5.0], [-5.0, -5.0, -5.0, -5.0]])
    np.testing.assert_allclose(x_corners, expected_x_corners)
    np.testing.assert_allclose(y_corners, expected_y_corners)

    x_corners, y_corners = get_projection_corners_from_centroids(x, y)
    np.testing.assert_allclose(x_corners, expected_x_corners)
    np.testing.assert_allclose(y_corners, expected_y_corners)

    # Case with only 1 dimension of size > 1
    x = np.array([0, 10, 20])
    y = np.array([0])
    x_corners, y_corners = get_projection_corners_from_1d_centroids(x, y)
    assert x_corners.shape == (2, 4), "Incorrect shape of corners"
    assert x_corners.shape == y_corners.shape, "Shape mismatch between x and y corners"
    expected_x_corners = np.array([[-5.0, 5.0, 15.0, 25.0], [-5.0, 5.0, 15.0, 25.0]])
    expected_y_corners = np.array([[5.0, 5.0, 5.0, 5.0], [-5.0, -5.0, -5.0, -5.0]])
    np.testing.assert_allclose(x_corners, expected_x_corners)
    np.testing.assert_allclose(y_corners, expected_y_corners)

    # Check case with only 1 dimension of size > 1 with dask array
    x = dask.array.from_array(np.array([0]))
    y = dask.array.from_array(np.array([0, 10, 20]))
    x_corners, y_corners = get_projection_corners_from_1d_centroids(x, y)
    assert x_corners.shape == (4, 2), "Incorrect shape of corners"
    assert x_corners.shape == y_corners.shape, "Shape mismatch between x and y corners"
    expected_x_corners = np.array([[-5.0, 5.0], [-5.0, 5.0], [-5.0, 5.0], [-5.0, 5.0]])
    expected_y_corners = np.array([[25.0, 25.0], [15.0, 15.0], [5.0, 5.0], [-5.0, -5.0]])
    np.testing.assert_allclose(x_corners.compute(), expected_x_corners)
    np.testing.assert_allclose(y_corners.compute(), expected_y_corners)

    x_corners, y_corners = get_projection_corners_from_centroids(x, y)
    np.testing.assert_allclose(x_corners, expected_x_corners)
    np.testing.assert_allclose(y_corners, expected_y_corners)

    # Case with only 1 value
    x = np.array([0])
    y = np.array([1])
    with pytest.raises(ValueError):
        get_projection_corners_from_1d_centroids(x, y)
    with pytest.raises(ValueError):
        get_projection_corners_from_centroids(x, y)


def test_get_projection_quadmesh_vertices():
    """Test getting projection quadmesh vertices."""
    x = np.array([[0, 10], [10, 20]])
    y = np.array([[0, 10], [10, 20]])
    quadmesh_vertices = get_projection_quadmesh_vertices(x, y)
    assert quadmesh_vertices.shape == (2, 2, 4, 2), "Shape mismatch for quadmesh vertices"
    np.testing.assert_allclose(quadmesh_vertices[0, 0, :, 0], np.array([-10.0, 0.0, 10.0, 0.0]))
    np.testing.assert_allclose(quadmesh_vertices[0, 0, :, 1], np.array([-10.0, 0.0, 10.0, 0.0]))


####---------------------------------------------------------------------------.
# TEST WRAPPERS
# TODO:
# get_quadmesh_centroids # gpm.quadmesh_centroids(crs=None)
# get_quadmesh_corners   # gpm.quadmesh_corners(crs=None)
# - get_projection_corners_from_centroids
# - get_lonlat_corners_from_centroids
# get_quadmesh_vertices  # gpm.quadmesh_vertices(crs=None, ccw=True)
# - get_lonlat_quadmesh_vertices
# - get_projection_quadmesh_vertices
# get_quadmesh_polygons  # gpm.quadmesh_polygons(crs=None)


####---------------------------------------------------------------------------.
#### Test get_quad mesh
# TODO: test corners output is always shape 2D
# TODO: test vertices output is always shape 4D (N,M,4,2)


# np_array = np.arange(10 * 10 * 2).reshape((10, 10, 2))

# order = "counterclockwise"
# vertices_np = _get_numpy_quad_mesh(np_array, order=order)


# da_array = da.from_array(np_array, chunks=(5, 5, 2))
# vertices_dask = get_quadmesh(da_array, order=order)

# assert vertices_dask.shape == vertices_np.shape
# np.allclose(vertices_dask.compute(), vertices_np)


# # 1D case

# # Extract cell vertices
# import numpy as np
# import xarray as xr
# import shapely

# x = da_dem_src["x"].data
# y = da_dem_src["y"].data

# x.shape
# y.shape

# #### Compute quadmesh
# x_bounds = xr.plot.utils._infer_interval_breaks(x)
# y_bounds = xr.plot.utils._infer_interval_breaks(y)
# x_bounds.shape
# y_bounds.shape


# x_corners, y_corners = np.meshgrid(x_bounds, y_bounds)
# # Quadmesh
# corners = np.stack((x_corners, y_corners), axis=2)
# corners.shape

# #### Compute Vertices
# ccw = True
# top_left = corners[:-1, :-1]
# top_right = corners[:-1, 1:]
# bottom_right = corners[1:, 1:]
# bottom_left = corners[1:, :-1]
# if ccw:
#     list_vertices = [top_left, bottom_left, bottom_right, top_right]
# else:
#     list_vertices = [top_left, top_right, bottom_right, bottom_left]
# vertices = np.stack(list_vertices, axis=2)
# vertices.shape
# vertices_flat = vertices.reshape(-1, 4, 2)
# vertices_flat.nbytes/1024/1024/1024 # 6GB
