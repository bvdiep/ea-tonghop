# Loader COLMAP dung pycolmap chinh thuc (khong can SceneManager cua nerfstudio).
# Dien vao cho gsplat simple_trainer.py: thay the file examples/datasets/colmap.py.
"""COLMAP dataset loader using pycolmap (official API).

Drop-in replacement for gsplat's examples/datasets/colmap.py which requires
nerfstudio's SceneManager (not shipped on PyPI). Exposes Parser and Dataset
with the same interface.
"""
import os
from typing import Any, Dict, List, Optional

import cv2
import imageio.v2 as imageio
import numpy as np
import pycolmap
import torch
from PIL import Image
from tqdm import tqdm
from typing_extensions import assert_never


def _get_rel_paths(path_dir: str) -> List[str]:
    paths = []
    for dp, dn, fn in os.walk(path_dir):
        for f in fn:
            paths.append(os.path.relpath(os.path.join(dp, f), path_dir))
    return paths


def _resize_image_folder(image_dir: str, resized_dir: str, factor: int) -> str:
    print(f"Downscaling images by {factor}x from {image_dir} to {resized_dir}.")
    os.makedirs(resized_dir, exist_ok=True)
    image_files = _get_rel_paths(image_dir)
    for image_file in tqdm(image_files):
        image_path = os.path.join(image_dir, image_file)
        resized_path = os.path.join(
            resized_dir, os.path.splitext(image_file)[0] + ".png"
        )
        if os.path.isfile(resized_path):
            continue
        image = imageio.imread(image_path)[..., :3]
        resized_size = (
            int(round(image.shape[1] / factor)),
            int(round(image.shape[0] / factor)),
        )
        resized_image = np.array(
            Image.fromarray(image).resize(resized_size, Image.BICUBIC)
        )
        imageio.imwrite(resized_path, resized_image)
    return resized_dir


def _cam_intrinsic(K: np.ndarray, factor: int) -> np.ndarray:
    K = K.copy()
    K[:2, :] /= factor
    return K


def _camtype(camera: pycolmap.Camera) -> str:
    m = camera.model_name.upper() if hasattr(camera, "model_name") else ""
    if m in ("SIMPLE_PINHOLE", "SIMPLE_RADIAL"):
        return "perspective"
    if m in ("PINHOLE", "OPENCV", "FULL_OPENCV", "RADIAL", "OPENCV_FISHEYE"):
        return "fisheye"
    if m == "ORTHO":
        return "ortho"
    return "perspective"


def _distortion_params(camera: pycolmap.Camera) -> np.ndarray:
    m = (camera.model_name or "").upper()
    p = np.asarray(camera.params, dtype=np.float32)
    if m in ("SIMPLE_PINHOLE", "PINHOLE"):
        return np.empty(0, dtype=np.float32)
    if m in ("SIMPLE_RADIAL", "RADIAL"):
        return np.array([p[3], p[4], 0.0, 0.0], dtype=np.float32)
    if m in ("OPENCV", "FULL_OPENCV"):
        return p[4:8].astype(np.float32)
    if m == "OPENCV_FISHEYE":
        return p[4:8].astype(np.float32)
    return p[4:8].astype(np.float32) if p.size > 4 else np.empty(0, dtype=np.float32)


class Parser:
    """COLMAP parser (pycolmap)."""

    def __init__(
        self,
        data_dir: str,
        factor: int = 1,
        normalize: bool = False,
        test_every: int = 8,
    ):
        self.data_dir = data_dir
        self.factor = factor
        self.normalize = normalize
        self.test_every = test_every

        colmap_dir = os.path.join(data_dir, "sparse", "0")
        if not os.path.exists(colmap_dir):
            colmap_dir = os.path.join(data_dir, "sparse")
        assert os.path.exists(
            colmap_dir
        ), f"COLMAP directory {colmap_dir} does not exist."

        rec = pycolmap.Reconstruction(colmap_dir)
        self.rec = rec

        # image_dir may be under data_dir (undistorted) or original
        image_dir = os.path.join(data_dir, "images")
        if not os.path.isdir(image_dir):
            image_dir = os.path.join(data_dir, "images_1")
        assert os.path.isdir(image_dir), f"image dir {image_dir} not found"

        if factor > 1:
            image_dir = _resize_image_folder(image_dir, os.path.join(data_dir, f"images_{factor}"), factor)

        imdata = rec.images
        w2c_mats = []
        camera_ids = []
        Ks_dict: Dict[int, np.ndarray] = {}
        params_dict: Dict[int, np.ndarray] = {}
        imsize_dict: Dict[int, tuple] = {}
        camtype_dict: Dict[int, str] = {}
        bottom = np.array([0, 0, 0, 1]).reshape(1, 4)

        # map from image name -> image object
        for image_id, im in imdata.items():
            cam = rec.cameras[im.camera_id]
            fx = float(cam.focal_length_x)
            fy = float(cam.focal_length_y)
            cx = float(cam.principal_point_x)
            cy = float(cam.principal_point_y)
            K = np.array(
                [[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]],
                dtype=np.float32,
            )
            Ks_dict[im.camera_id] = _cam_intrinsic(K, factor)
            params_dict[im.camera_id] = _distortion_params(cam)
            imsize_dict[im.camera_id] = (int(cam.width), int(cam.height))
            camtype_dict[im.camera_id] = _camtype(cam)

            # cam_from_world: R + tvec (COLMAP qvec -> rotation)
            c2w = im.cam_from_world()  # method in pycolmap 4.x
            R = np.asarray(c2w.rotation.matrix())
            t = np.asarray(c2w.translation).reshape(3, 1)
            w2c = np.concatenate([np.concatenate([R, t], 1), bottom], axis=0)
            w2c_mats.append(w2c)
            camera_ids.append(im.camera_id)

        w2c_mats = np.stack(w2c_mats, axis=0)
        camera_ids = np.array(camera_ids, dtype=np.int32)

        # sort images by name to keep deterministic ordering
        names = [imdata[i].name for i in imdata.keys()]
        order = np.argsort(names)
        w2c_mats = w2c_mats[order]
        camera_ids = camera_ids[order]
        self.names = [names[i] for i in order]

        self.image_dir = image_dir
        self.image_names = self.names
        self.Ks = Ks_dict
        self.params = params_dict
        self.imsize = imsize_dict
        self.camtype = camtype_dict
        self.w2c_mats = w2c_mats
        self.camera_ids = camera_ids
        self.camera_indices = camera_ids  # gsplat expects per-image camera idx

        # points3D
        pts = rec.points3D
        if len(pts) > 0:
            xyz = np.array([p.xyz for p in pts.values()], dtype=np.float32)
            rgb = np.array([p.color for p in pts.values()], dtype=np.float32)
            self.points = xyz
            self.points_rgb = rgb
        else:
            self.points = np.zeros((0, 3), dtype=np.float32)
            self.points_rgb = np.zeros((0, 3), dtype=np.float32)

        # normalize world space
        self.scene_scale = float(np.linalg.norm(w2c_mats[:, :3, 3], axis=1).max()) if len(w2c_mats) else 1.0
        if normalize:
            pts_xyz = self.points
            if pts_xyz.shape[0] > 0:
                scene_center = np.mean(pts_xyz, axis=0)
            else:
                scene_center = np.mean(w2c_mats[:, :3, 3], axis=0)
            self.scene_center = scene_center
            dists = np.linalg.norm(w2c_mats[:, :3, 3] - scene_center, axis=1)
            self.scene_scale = float(np.max(dists))
        else:
            self.scene_center = np.zeros(3, dtype=np.float32)
            self.scene_scale = 1.0

        self.cam_from_gs = np.eye(4, dtype=np.float32)

    def __len__(self):
        return len(self.image_names)


class Dataset:
    """Simple COLMAP dataset."""

    def __init__(
        self,
        parser: Parser,
        split: str = "train",
        batch_size: int = 1,
        test_every: Optional[int] = None,
        load_depths: bool = False,
    ):
        self.parser = parser
        self.split = split
        self.batch_size = batch_size
        self.load_depths = load_depths

        n = len(parser)
        if test_every is None:
            test_every = parser.test_every
        test_idx = np.arange(0, n, test_every)
        train_idx = np.array([i for i in range(n) if i not in set(test_idx.tolist())])

        if split == "train":
            self.indices = train_idx
        elif split == "val":
            self.indices = test_idx
        elif split == "test":
            self.indices = test_idx
        else:
            assert_never(split)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index: int) -> Dict[str, Any]:
        parser = self.parser
        i = self.indices[index]
        name = parser.image_names[i]
        cam_id = int(parser.camera_indices[i])
        K = parser.Ks[cam_id]
        params = parser.params[cam_id]
        camtype = parser.camtype[cam_id]
        w2c = parser.w2c_mats[i]

        image_path = os.path.join(parser.image_dir, name)
        image = imageio.imread(image_path)[..., :3] / 255.0
        h, w = image.shape[:2]

        # apply cam_from_gs (gsplat convention: camera -> gs frame)
        c2w = np.linalg.inv(w2c)
        c2w = parser.cam_from_gs @ c2w

        data = {
            "image": torch.from_numpy(image).float(),
            "K": torch.from_numpy(K).float(),
            "cam_from_world": torch.from_numpy(c2w).float(),
            "image_name": name,
            "camera_idx": cam_id,
        }
        if params.size > 0:
            data["distortion_params"] = torch.from_numpy(params).float()
        if camtype == "fisheye":
            data["camera_model"] = "fisheye"
        else:
            data["camera_model"] = "pinhole"
        return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data/360_v2/garden")
    parser.add_argument("--factor", type=int, default=4)
    args = parser.parse_args()

    p = Parser(data_dir=args.data_dir, factor=args.factor, normalize=True, test_every=8)
    dataset = Dataset(p, split="train")
    print(f"Dataset: {len(dataset)} images, scene_scale={p.scene_scale:.3f}")
    d = dataset[0]
    print({k: (v.shape if hasattr(v, "shape") else v) for k, v in d.items()})
