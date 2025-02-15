import numpy as np
from scipy import ndimage
import pandas as pd


def compute_bounding_box(mask_gt, mask_pred, exclusion_zone):
    """

    :param mask_gt:
    :param mask_pred:
    :param exclusion_zone:
    :return:
    """
    mask_all = mask_gt | mask_pred
    mask_all = mask_all | exclusion_zone
    bbox_min = np.zeros(3, np.int64)
    bbox_max = np.zeros(3, np.int64)

    # max projection to the x0-axis
    proj_0 = np.max(np.max(mask_all, axis=2), axis=1)
    idx_nonzero_0 = np.nonzero(proj_0)[0]

    bbox_min[0] = np.min(idx_nonzero_0)
    bbox_max[0] = np.max(idx_nonzero_0)

    # max projection to the x1-axis
    proj_1 = np.max(np.max(mask_all, axis=2), axis=0)
    idx_nonzero_1 = np.nonzero(proj_1)[0]
    bbox_min[1] = np.min(idx_nonzero_1)
    bbox_max[1] = np.max(idx_nonzero_1)

    # max projection to the x2-axis
    proj_2 = np.max(np.max(mask_all, axis=1), axis=0)
    idx_nonzero_2 = np.nonzero(proj_2)[0]
    bbox_min[2] = np.min(idx_nonzero_2)
    bbox_max[2] = np.max(idx_nonzero_2)

    return bbox_min, bbox_max


def crop_mask(mask, bbox_min, bbox_max):
    cropmask = np.zeros((bbox_max - bbox_min) + 2)

    cropmask[0:-1, 0:-1, 0:-1] = mask[bbox_min[0]:bbox_max[0] + 1,
                                 bbox_min[1]:bbox_max[1] + 1,
                                 bbox_min[2]:bbox_max[2] + 1]
    return cropmask


def compute_distances(mask_gt, mask_pred, exclusion_zone, spacing_mm, connectivity=1, crop=True, exclusion_distance=5):
    """
    Function computing the surface distances between 2 binary segmentation Nifti images.
    :param mask_gt: tumor file in Nifti (NiBabel) format
    :param mask_pred: ablation file in Nifti (NiBabel) format
    :param exclusion_zone: liver file Nifti (NiBabel) format
    :param spacing_mm: spacing extracted from the Nifti files provided above. spacing should be the same for all.
    :param connectivity: connectivity factor for defining the kernel size needed to extract the contours
    :param crop: True (default) /False. Whether to crop the files around the ROI. When True computation time is faster.
    :param exclusion_distance: The exclusion distance to "remove" voxels from the liver capsule within this distance. Works only for subcapsular cases when liver segmentation provided.
    :return: Dictionary of Arrays containing the Surface Distances, Distance Maps and Border Values.
    """
    if crop:
        if exclusion_zone is not None:
            bbox_min, bbox_max = compute_bounding_box(mask_gt, mask_pred, exclusion_zone)
            mask_gt = crop_mask(mask_gt, bbox_min, bbox_max).astype(bool)
            mask_pred = crop_mask(mask_pred, bbox_min, bbox_max).astype(bool)
            exclusion_zone = crop_mask(exclusion_zone, bbox_min, bbox_max).astype(bool)
        else:
            bbox_min, bbox_max = compute_bounding_box(mask_gt, mask_pred, mask_gt)
            mask_gt = crop_mask(mask_gt, bbox_min, bbox_max).astype(bool)
            mask_pred = crop_mask(mask_pred, bbox_min, bbox_max).astype(bool)

    border_inside = ndimage.binary_erosion(mask_gt, structure=ndimage.generate_binary_structure(3, connectivity))
    borders_gt = mask_gt ^ border_inside
    border_inside = ndimage.binary_erosion(mask_pred, structure=ndimage.generate_binary_structure(3, connectivity))
    borders_pred = mask_pred ^ border_inside

    # compute the distance transform (closest distance of each voxel to the surface voxels)
    if borders_gt.any():
        distmap_gt = ndimage.morphology.distance_transform_edt(
            ~borders_gt, sampling=spacing_mm)
        distmask_gt = mask_gt.astype(np.int8)
        distmask_gt[distmask_gt == 0] = -1
        distmap_gt *= distmask_gt
    else:
        distmap_gt = np.Inf * np.ones(borders_gt.shape)

    if borders_pred.any():
        distmap_pred = ndimage.morphology.distance_transform_edt(
            ~borders_pred, sampling=spacing_mm)
        distmask_pred = mask_pred.astype(np.int8)
        distmask_pred[distmask_pred == 0] = -1
        distmap_pred *= distmask_pred
    else:
        distmap_pred = np.Inf * np.ones(borders_pred.shape)

    if exclusion_zone is not None:
        border_inside = ndimage.binary_erosion(exclusion_zone,
                                               structure=ndimage.generate_binary_structure(3, connectivity))
        borders_exclusion = exclusion_zone ^ border_inside
        distmap_exclusion = ndimage.morphology.distance_transform_edt(
            ~borders_exclusion, sampling=spacing_mm)

        distmask_exclusion = exclusion_zone.astype(np.int8)
        distmask_exclusion[distmask_exclusion == 0] = -1
        distmap_exclusion *= distmask_exclusion

        borders_pred[distmap_exclusion < exclusion_distance] = 0
        borders_gt[distmap_exclusion < exclusion_distance] = 0

    # create a list of all surface elements with distance and area
    distances_gt_to_pred = distmap_pred[borders_gt > 0]
    distances_pred_to_gt = distmap_gt[borders_pred > 0]

    return {"distances_gt_to_pred": distances_gt_to_pred,
            "distances_pred_to_gt": distances_pred_to_gt,
            "borders_gt": borders_gt,
            "borders_pred": borders_pred,
            "distmap_gt": distmap_gt,
            "distmap_pred": distmap_pred,
            "distmask_pred": distmask_pred,
            "border_exclusion": borders_exclusion if exclusion_zone is not None else None,
            "distmap_exclusion": distmap_exclusion if exclusion_zone is not None else None}


def summarize_surface_dists(patient_id, lesion_id, surface_distance):
    """
    Function summarizing the surface distances (descriptive stats).
    :param patient_id: Patient Name
    :param lesion_id: Lesion Number (e.g. 1, 2, 3)..
    :param surface_distance: Dict Object containing all the surface distances.
    :return:
    """
    distances = surface_distance['distances_gt_to_pred']
    nr_voxels = len(distances)
    min_distance = np.nanmin(distances)
    q25_distance = np.nanquantile(distances, 0.25)
    median_distance = np.nanmedian(distances)
    q75_distance = np.nanquantile(distances, 0.75)
    max_distance = np.nanmax(distances)

    non_ablated = np.sum(distances < 0.0) / nr_voxels
    insuffiecient_ablated = np.sum(distances < 5.0) / nr_voxels
    completely_ablated = np.sum(distances >= 5.0) / nr_voxels

    coverage_data = {'Patient': patient_id,
                     'Lesion': lesion_id,
                     'nr_voxels': nr_voxels,
                     'min_distance': min_distance,
                     'q25_distance': q25_distance,
                     'median_distance': median_distance,
                     'q75_distance': q75_distance,
                     'max_distance': max_distance,
                     'x_less_than_0mm': non_ablated,
                     'x_equal_greater_than_0m': insuffiecient_ablated,
                     'x_equal_greater_than_5m': completely_ablated}

    df = pd.DataFrame([coverage_data])
    return df
