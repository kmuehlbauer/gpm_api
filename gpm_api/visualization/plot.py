#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 10 18:42:28 2022

@author: ghiggi
"""
import numpy as np
import cartopy
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from gpm_api.utils.utils_cmap import get_colormap_setting


### TODO: Add xarray + cartopy  (xr_carto) (xr_mpl)
# _plot_cartopy_xr_imshow
# _plot_cartopy_xr_pcolormesh


# TODO: modify ticklabels in all get_colorbar_settings in  grid and orbit 
# def get_colorbar_settings(name):
#     # TODO: to customize as function of da.name
#     plot_kwargs, cbar_kwargs, ticklabels = get_colormap_setting("pysteps_mm/hr")
#     return (plot_kwargs, cbar_kwargs, ticklabels)

def _preprocess_figure_args(ax, fig_kwargs, subplot_kwargs):
    if ax is not None: 
        if len(subplot_kwargs) >= 1:
            raise ValueError("Provide `subplot_kwargs`only if `ax`is None")
        if len(fig_kwargs) >= 1:
            raise ValueError("Provide `fig_kwargs` only if `ax`is None") 
    
    # If ax is not specified, specify the figure defaults
    # if ax is None:
        # Set default figure size and dpi  
        # fig_kwargs['figsize'] = (12, 10)
        # fig_kwargs['dpi'] = 100

def _preprocess_subplot_kwargs(subplot_kwargs):
    subplot_kwargs = subplot_kwargs.copy()
    if "projection" not in subplot_kwargs:
        subplot_kwargs["projection"] = ccrs.PlateCarree()
    return subplot_kwargs
        

def get_colorbar_settings(name, plot_kwargs={}, cbar_kwargs={}):
    # TODO: to customize as function of da.name
    try: 
        default_plot_kwargs, default_cbar_kwargs, default_ticklabels = get_colormap_setting(name)
        default_cbar_kwargs['ticklabels'] = None
    except: 
        default_plot_kwargs = {}
        default_cbar_kwargs = {}
        default_ticklabels = None # to be placed in cbar_kwargs
        
    # If the default is a segmented colormap (with ticks and ticklabels)
    if default_cbar_kwargs.get("ticks", None) is not None:
        # If specifying a custom vmin, vmax, norm or cmap args, remove  the defaults
        # - The discrete colorbar makes no sense anymore
        if np.any(np.isin(["vmin","vmax", "norm", "cmap"], list(plot_kwargs.keys()))):
            default_cbar_kwargs.pop("ticks", None)
            default_cbar_kwargs.pop("ticklabels", None)
            default_plot_kwargs.pop("cmap", None)
            default_plot_kwargs.pop("norm", None)
            default_plot_kwargs.pop("vmin", None)
            default_plot_kwargs.pop("vmax", None)
    
    # If cmap is a string, retrieve colormap 
    if isinstance(plot_kwargs.get("cmap", None), str): 
        plot_kwargs["cmap"] = plt.get_cmap(plot_kwargs["cmap"])
                     
    # Update defaults with custom kwargs 
    default_plot_kwargs.update(plot_kwargs)
    default_cbar_kwargs.update(cbar_kwargs)
    
    # Return the kwargs 
    plot_kwargs = default_plot_kwargs
    cbar_kwargs = default_cbar_kwargs
    return (plot_kwargs, cbar_kwargs)


def get_extent(da, x="lon", y="lat"):
    # TODO: compute corners array to estimate the extent
    # - OR increase by 1° in everydirection and then wrap between -180, 180,90,90
    # Get the minimum and maximum longitude and latitude values
    lon_min, lon_max = da[x].min(), da[x].max()
    lat_min, lat_max = da[y].min(), da[y].max()
    extent = (lon_min, lon_max, lat_min, lat_max)
    return extent


def get_antimeridian_mask(lons, buffer=True):
    """Get mask of longitude coordinates neighbors crossing the antimeridian."""
    from scipy.ndimage import binary_dilation

    # Check vertical edges
    row_idx, col_idx = np.where(np.abs(np.diff(lons, axis=0)) > 180)
    row_idx_rev, col_idx_rev = np.where(np.abs(np.diff(lons[::-1, :], axis=0)) > 180)
    row_idx_rev = lons.shape[0] - row_idx_rev - 1
    row_indices = np.append(row_idx, row_idx_rev)
    col_indices = np.append(col_idx, col_idx_rev)
    # Check horizontal
    row_idx, col_idx = np.where(np.abs(np.diff(lons, axis=1)) > 180)
    row_idx_rev, col_idx_rev = np.where(np.abs(np.diff(lons[:, ::-1], axis=1)) > 180)
    col_idx_rev = lons.shape[1] - col_idx_rev - 1
    row_indices = np.append(row_indices, np.append(row_idx, row_idx_rev))
    col_indices = np.append(col_indices, np.append(col_idx, col_idx_rev))
    # Create mask
    mask = np.zeros(lons.shape)
    mask[row_indices, col_indices] = 1
    # Buffer by 1 in all directions to ensure edges not crossing the antimeridian
    mask = binary_dilation(mask)
    return mask


####--------------------------------------------------------------------------.
def plot_cartopy_background(ax):
    """Plot cartopy background."""
    # - Add coastlines
    ax.coastlines()
    ax.add_feature(cartopy.feature.LAND, facecolor=[0.9, 0.9, 0.9])
    ax.add_feature(cartopy.feature.OCEAN, alpha=0.6)
    ax.add_feature(cartopy.feature.STATES)
    # - Add grid lines
    gl = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=1,
        color="gray",
        alpha=0.1,
        linestyle="-",
    )
    gl.top_labels = False  # gl.xlabels_top = False
    gl.right_labels = False  # gl.ylabels_right = False
    gl.xlines = True
    gl.ylines = True
    return ax


def plot_colorbar(p, ax, cbar_kwargs={}):
    """Add a colorbar to a matplotlib/cartopy plot.

    p: matplotlib.image.AxesImage
    ax:  cartopy.mpl.geoaxes.GeoAxesSubplot
    """
    ticklabels = cbar_kwargs.pop("ticklabels", None)
    divider = make_axes_locatable(ax)
    cax = divider.new_horizontal(size="5%", pad=0.1, axes_class=plt.Axes)
    p.figure.add_axes(cax)
    cbar = plt.colorbar(p, cax=cax, ax=ax, **cbar_kwargs)
    if ticklabels is not None:
        _ = cbar.ax.set_yticklabels(ticklabels)
    return cbar

####--------------------------------------------------------------------------.
def _plot_cartopy_imshow(
    ax,
    da,
    x,
    y,
    interpolation="nearest",
    add_colorbar=True, 
    plot_kwargs={},
    cbar_kwargs={},
):
    """Plot imshow with cartopy."""
    # - Ensure image with correct dimensions orders
    da = da.transpose(y, x)
    arr = da.data.compute()

    # - Derive extent
    extent = [-180, 180, -90, 90]  # TODO: Derive from data !!!!

    # - Add variable field with cartopy
    p = ax.imshow(
        arr,
        transform=ccrs.PlateCarree(),
        extent=extent,
        origin="upper",
        interpolation=interpolation,
        **plot_kwargs,
    )
    # - Set the extent
    extent = get_extent(da, x="lon", y="lat")
    ax.set_extent(extent)

    # - Add colorbar
    if add_colorbar:
        # --> TODO: set axis proportion in a meaningful way ...
        _ = plot_colorbar(p=p, ax=ax, cbar_kwargs=cbar_kwargs)
    return p


def _plot_cartopy_pcolormesh(
    ax,
    da,
    x,
    y,
    add_colorbar=True,
    plot_kwargs={},
    cbar_kwargs={},
):
    """Plot imshow with cartopy.

    The function currently does not allow to zoom on regions across the antimeridian.
    The function mask scanning pixels which spans across the antimeridian.
    """
    # TODO: plot antimeridian crossing cells with PolyCollection

    # - Get x, y, and array to plot
    da = da.compute()
    x = da[x].data
    y = da[y].data
    arr = da.data

    # - Mask cells crossing the antimeridian
    mask = get_antimeridian_mask(x, buffer=True)
    if np.any(mask):
        arr = np.ma.masked_where(mask, arr)
        # Sanitize cmap bad color to avoid cartopy bug
        if "cmap" in plot_kwargs:
            cmap = plot_kwargs["cmap"]
            bad = cmap.get_bad()
            bad[3] = 0  # enforce to 0 (transparent)
            cmap.set_bad(bad)
            plot_kwargs["cmap"] = cmap

    # - Add variable field with cartopy
    p = ax.pcolormesh(
        x,
        y,
        arr,
        transform=ccrs.PlateCarree(),
        **plot_kwargs,
    )

    # - Set the extent
    # --> To be set in projection coordinates of crs !!!
    #     lon/lat conversion to proj required !
    # extent = get_extent(da, x="lon", y="lat")
    # ax.set_extent(extent)
    
    # - Add colorbar
    if add_colorbar:
        # --> TODO: set axis proportion in a meaningful way ...
        _ = plot_colorbar(p=p, ax=ax, cbar_kwargs=cbar_kwargs)
    return p


def _plot_mpl_imshow(
    ax,
    da,
    x,
    y,
    interpolation="nearest",
    add_colorbar=True, 
    plot_kwargs={},
    cbar_kwargs={},
):
    """Plot imshow with matplotlib."""
    # - Ensure image with correct dimensions orders
    da = da.transpose(y, x)
    arr = da.data.compute()

    # - Add variable field with matplotlib
    p = ax.imshow(
        arr,
        origin="upper",
        interpolation=interpolation,
        **plot_kwargs,
    )
    # - Add colorbar
    if add_colorbar:
        # --> TODO: set axis proportion in a meaningful way ...
        _ = plot_colorbar(p=p, ax=ax, cbar_kwargs=cbar_kwargs)
    # - Return mappable
    return p


def _plot_xr_imshow(
    ax, da, x, y,
    interpolation="nearest",
    add_colorbar=True, 
    plot_kwargs={},
    cbar_kwargs={},
):
    """Plot imshow with xarray."""
    # --> BUG with colorbar: https://github.com/pydata/xarray/issues/7014
    ticklabels = cbar_kwargs.pop("ticklabels", None)
    p = da.plot.imshow(
        x=x,
        y=y,
        ax=ax,
        interpolation=interpolation,
        add_colorbar=add_colorbar,
        cbar_kwargs=cbar_kwargs,
        **plot_kwargs,
    )
    if add_colorbar:
        p.colorbar.ax.set_yticklabels(ticklabels)
    return p


####--------------------------------------------------------------------------.
def plot_map(
    da,
    ax=None,
    add_colorbar=True,
    add_swath_lines=True,    # used only for GPM orbit objects
    interpolation="nearest", # used only for GPM grid objects
    fig_kwargs={}, 
    subplot_kwargs={},
    cbar_kwargs={},
    **plot_kwargs,
):

    from gpm_api.utils.geospatial import is_orbit, is_grid
    from .grid import plot_grid_map
    from .orbit import plot_orbit_map
    # Plot orbit
    if is_orbit(da):
        p = plot_orbit_map(
            da=da,
            ax=ax,
            add_colorbar=add_colorbar,
            add_swath_lines=add_swath_lines, 
            fig_kwargs=fig_kwargs, 
            subplot_kwargs=subplot_kwargs,
            cbar_kwargs=cbar_kwargs,
            **plot_kwargs,
        )
    # Plot grid
    elif is_grid(da):
        p = plot_grid_map(
            da=da,
            ax=ax,
            add_colorbar=add_colorbar,
            interpolation=interpolation,
            fig_kwargs=fig_kwargs, 
            subplot_kwargs=subplot_kwargs,
            cbar_kwargs=cbar_kwargs,
            **plot_kwargs,
        )
    else:
        raise ValueError("Can not plot. It's neither a GPM grid, neither a GPM orbit.")
    # Return mappable
    return p


def plot_image(
    da, ax=None, 
    add_colorbar=True, 
    interpolation="nearest",
    fig_kwargs={}, 
    cbar_kwargs={},
    **plot_kwargs,
):
    # figsize, dpi, subplot_kw only used if ax is None
    from gpm_api.utils.geospatial import is_orbit, is_grid
    from gpm_api.visualization.grid import plot_grid_image
    from gpm_api.visualization.orbit import plot_orbit_image

    # Plot orbit
    if is_orbit(da):
        p = plot_orbit_image(
            da=da,
            ax=ax,
            add_colorbar=add_colorbar,
            interpolation=interpolation,
            fig_kwargs=fig_kwargs, 
            cbar_kwargs=cbar_kwargs,
            **plot_kwargs,
        )
    # Plot grid
    elif is_grid(da):
        p = plot_grid_image(
            da=da,
            ax=ax,
            add_colorbar=add_colorbar,
            interpolation=interpolation,
            fig_kwargs=fig_kwargs, 
            cbar_kwargs=cbar_kwargs,
            **plot_kwargs,
        )
    else:
        raise ValueError("Can not plot. It's neither a GPM GRID, neither a GPM ORBIT.")
    # Return mappable
    return p


def plot_map_mesh(
    da,
    ax=None,
    edgecolors="k",
    fig_kwargs={}, 
    subplot_kwargs={},
    cbar_kwargs={},
    **plot_kwargs,
):
    # Interpolation only for grid objects
    # figsize, dpi, subplot_kw only used if ax is None
    from gpm_api.utils.geospatial import is_orbit, is_grid

    # from .grid import plot_grid_mesh
    from .orbit import plot_orbit_mesh

    # Plot orbit
    if is_orbit(da):
        p = plot_orbit_mesh(
            da=da,
            ax=ax,
            edgecolors=edgecolors,
            fig_kwargs=fig_kwargs, 
            subplot_kwargs=subplot_kwargs,
            cbar_kwargs=cbar_kwargs,
            **plot_kwargs,
        )
    # Plot grid
    elif is_grid(da):
        raise NotImplementedError("Not yet implemented.")
        #     p = plot_grid_mesh(
        #         da=da,
        #         ax=ax,
        #         edgecolors=edgecolors,
        #         subplot_kw=subplot_kw,
        #         figsize=figsize,
        #         dpi=dpi,
        #     )
        # else:
        raise ValueError("Can not plot. It's neither a GPM grid, neither a GPM orbit.")
    # Return mappable
    return p
