import sys
import os
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import torch
from PIL import Image as PILImage

# ----------------------------
# PATH
# ----------------------------
sam3_root = "./vision/sam3/sam3"
sys.path.insert(0, "./vision/sam3")

from sam3 import build_sam3_image_model

from sam3.train.data.collator import collate_fn_api as collate
from sam3.model.utils.misc import copy_data_to_device

from sam3.train.data.sam3_image_dataset import (
    InferenceMetadata,
    FindQueryLoaded,
    Image as SAMImage,
    Datapoint,
)

from sam3.train.transforms.basic_for_api import (
    ComposeAPI,
    RandomResizeAPI,
    ToTensorAPI,
    NormalizeAPI,
)

from sam3.eval.postprocessors import PostProcessImage

from sam3.visualization_utils import plot_results

class SAM3BatchProcessor:
    """Processor responsible for managing batch inference operations using the SAM3 model.

    This class handles the initialization of the Segment Anything Model 3 (SAM3), 
    manages dataset prompt preparation (textual and visual), runs batch inferences 
    with custom hardware performance optimization configurations, and processes/merges 
    the resulting segmentations.

    Args:
        sam3_root (str):
            The root directory path of the SAM3 repository assets. Defaults to "./sam3/sam3".
        confidence_threshold (float):
            The minimum score requirement for keeping a detection mask. Defaults to 0.5.
        device (str):
            The processing hardware device execution target. Defaults to "cuda".

    """
    
    def __init__(
        self,
        sam3_root="./sam3/sam3",
        confidence_threshold=0.5,
        device="cuda",
    ):

        self.sam3_root = sam3_root
        self.device = torch.device(device)

        # ---------------------------------
        # PERF
        # ---------------------------------
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

        # ---------------------------------
        # MODEL
        # ---------------------------------
        bpe_path = os.path.join(
            sam3_root,
            "assets",
            "bpe_simple_vocab_16e6.txt.gz"
        )

        self.model = build_sam3_image_model(
            bpe_path=bpe_path
        )

        self.model = self.model.to(self.device)
        self.model.eval()

        # ---------------------------------
        # TRANSFORM
        # ---------------------------------
        self.transform = ComposeAPI(
            transforms=[
                RandomResizeAPI(
                    sizes=1008,
                    max_size=1008,
                    square=True,
                    consistent_transform=False,
                ),
                ToTensorAPI(),
                NormalizeAPI(
                    mean=[0.5, 0.5, 0.5],
                    std=[0.5, 0.5, 0.5],
                ),
            ]
        )

        # ---------------------------------
        # POSTPROCESSOR
        # ---------------------------------
        self.postprocessor = PostProcessImage(
            max_dets_per_img=-1,
            iou_type="segm",
            use_original_sizes_box=True,
            use_original_sizes_mask=True,
            convert_mask_to_rle=False,
            detection_threshold=confidence_threshold,
            to_cpu=False,
        )

        # ---------------------------------
        # COUNTER
        # ---------------------------------
        self.global_counter = 1

    # =========================================================
    # DATAPOINT
    # =========================================================

    def create_datapoint(self):
        """Instantiate an empty placeholder Datapoint structure.

        Returns:
            An empty Datapoint instance ready to collect query prompts and target images.

        """
        return Datapoint(
            find_queries=[],
            images=[]
        )

    def set_image(self, datapoint : Datapoint, pil_image : PILImage):
        """Bind a target PIL Image data matrix wrapper to an existing Datapoint.

        Args:
            datapoint (Datapoint):
                The destination data object structure to update.
            pil_image (PIL.Image):
                The source raw PIL Image reference matrix.

        """
        w, h = pil_image.size

        datapoint.images = [
            SAMImage(
                data=pil_image,
                objects=[],
                size=[h, w]
            )
        ]

    # =========================================================
    # PROMPTS
    # =========================================================

    def add_text_prompt(
        self,
        datapoint : Datapoint,
        text_query : str,
    ) -> int:
        """Append a textual query descriptor prompt instruction to a target Datapoint.

        Args:
            datapoint (Datapoint):
                The data object structure where the text prompt should be added.
            text_query (str):
                The semantic search string or keyword representing the object to find.

        Returns:
            The newly registered unique integer tracking identification number.

        """
        assert len(datapoint.images) == 1

        w, h = datapoint.images[0].size

        prompt_id = self.global_counter

        datapoint.find_queries.append(
            FindQueryLoaded(
                query_text=text_query,
                image_id=0,
                object_ids_output=[],
                is_exhaustive=True,
                query_processing_order=0,
                inference_metadata=InferenceMetadata(
                    coco_image_id=prompt_id,
                    original_image_id=prompt_id,
                    original_category_id=1,
                    original_size=[w, h],
                    object_id=0,
                    frame_index=0,
                )
            )
        )

        self.global_counter += 1

        return prompt_id

    def add_visual_prompt(
        self,
        datapoint : Datapoint,
        boxes: list[list[float]],
        labels: list[bool],
        text_prompt="visual",
    ) -> int:
        """Append a bounding box context layout visual prompt restriction map to a target Datapoint.

        Args:
            datapoint (Datapoint):
                The data object structure where the visual prompt should be added.
            boxes (List[List[float]]):
                A nested structure of bounding boxes mapping coordinate fields.
            labels (List[bool]):
                A collection of boolean markers validating targeted bounding elements.
            text_prompt (str):
                The baseline semantic text tag anchor identifier. Defaults to "visual".

        Returns:
            The newly registered unique integer tracking identification number.

        """
        assert len(datapoint.images) == 1
        assert len(boxes) > 0
        assert len(boxes) == len(labels)

        for b in boxes:
            assert len(b) == 4

        labels_tensor = torch.tensor(
            labels,
            dtype=torch.bool
        ).view(-1)

        w, h = datapoint.images[0].size

        prompt_id = self.global_counter

        datapoint.find_queries.append(
            FindQueryLoaded(
                query_text=text_prompt,
                image_id=0,
                object_ids_output=[],
                is_exhaustive=True,
                query_processing_order=0,
                input_bbox=torch.tensor(
                    boxes,
                    dtype=torch.float
                ).view(-1, 4),
                input_bbox_label=labels_tensor,
                inference_metadata=InferenceMetadata(
                    coco_image_id=prompt_id,
                    original_image_id=prompt_id,
                    original_category_id=1,
                    original_size=[w, h],
                    object_id=0,
                    frame_index=0,
                )
            )
        )

        self.global_counter += 1

        return prompt_id

    # =========================================================
    # INFERENCE
    # =========================================================

    def process(
        self,
        datapoints: list[Datapoint],
    ):
        """Execute raw model forward pass inference steps across a collection of Datapoints.

        Args:
            datapoints (List[Datapoint]):
                A list of loaded context Datapoint collections to feed to the network.

        Returns:
            The raw structured results dictionary extracted directly from the postprocessor block.

        """
        transformed = [
            self.transform(dp)
            for dp in datapoints
        ]

        batch = collate(
            transformed,
            dict_key="dummy"
        )["dummy"]

        batch = copy_data_to_device(
            batch,
            self.device,
            non_blocking=True
        )

        with torch.inference_mode():

            with torch.autocast(
                device_type="cuda",
                dtype=torch.bfloat16
            ):

                output = self.model(batch)

        processed_results = (
            self.postprocessor.process_results(
                output,
                batch.find_metadatas
            )
        )

        return processed_results

    # =========================================================
    # MERGE
    # =========================================================

    def normalize_masks(self, m):
        """Sanitize raw output masks to guarantee a 3-dimensional tensor layout.

        Args:
            m (torch.Tensor):
                The target segmentation mask array structure to reshape.

        Returns:
            A normalized tensor matching an absolute [N, H, W] dimension shape.

        """
        if not torch.is_tensor(m):
            return None

        # remove useless leading dims
        while m.ndim > 3 and m.shape[0] == 1:
            m = m.squeeze(0)

        # ensure shape = [N, H, W]
        if m.ndim == 4:
            m = m.squeeze(1)

        return m

    def merge_sam3_results(self, processed_results):
        """Concatenate detached batch inference evaluation outputs into shared array maps.

        Args:
            processed_results (List[dict]):
                A series of raw individual inference dictionary output blocks.

        Returns:
            A unified collection map pairing grouped tensors across uniform key definitions.

        """
        merged = {
            "scores": [],
            "boxes": [],
            "masks": [],
            "labels": []
        }

        for r in processed_results:

            if not isinstance(r, dict):
                continue

            # -----------------------------
            # BOXES
            # -----------------------------
            if "boxes" in r and torch.is_tensor(r["boxes"]):

                b = r["boxes"]

                # force -> [N,4]
                if b.ndim == 1:
                    b = b.view(1, 4)

                elif b.ndim == 3:
                    b = b.view(-1, 4)

                merged["boxes"].append(b)

            # -----------------------------
            # SCORES
            # -----------------------------
            if "scores" in r and torch.is_tensor(r["scores"]):

                s = r["scores"].view(-1)

                merged["scores"].append(s)

            # -----------------------------
            # MASKS
            # -----------------------------
            if "masks" in r and torch.is_tensor(r["masks"]):

                m = r["masks"]

                # force -> [N,1,H,W]
                if m.ndim == 3:
                    m = m.unsqueeze(1)

                merged["masks"].append(m)

            # -----------------------------
            # LABELS
            # -----------------------------
            if "labels" in r and torch.is_tensor(r["labels"]):

                l = r["labels"].view(-1)

                merged["labels"].append(l)

        # -----------------------------------------
        # CONCAT
        # -----------------------------------------

        out = {}

        for k, values in merged.items():

            if len(values) == 0:
                out[k] = None
                continue

            try:
                out[k] = torch.cat(values, dim=0)

            except Exception as e:
                print(f"[MERGE ERROR] {k}: {e}")
                out[k] = values[0]

        return out

    def merge_to_single_object(
        self,
        processed_results: dict[int, dict[str, Any]]
    ):
        """Condense scattered multiple target results into an isolated single item representation.

        Args:
            processed_results (Dict[int, Dict[str, Any]]):
                An identification-mapped dictionary tracking sub-component metrics.

        Returns:
            A grouped summary data dictionary holding unified metrics, boxes, and union masks.

        """
        masks = []
        boxes = []
        scores = []

        for _, result in processed_results.items():

            if "masks" in result:
                masks.append(result["masks"])

            if "boxes" in result:
                boxes.append(result["boxes"])

            if "scores" in result:
                scores.append(result["scores"])

        # -----------------------------------
        # MASK UNION
        # -----------------------------------

        merged_mask = None

        if len(masks) > 0:

            merged_mask = masks[0]

            for m in masks[1:]:
                merged_mask = merged_mask | m

        # -----------------------------------
        # BOX UNION
        # -----------------------------------

        merged_box = None

        if len(boxes) > 0:

            all_boxes = torch.cat(boxes, dim=0)

            x1 = all_boxes[:, 0].min()
            y1 = all_boxes[:, 1].min()
            x2 = all_boxes[:, 2].max()
            y2 = all_boxes[:, 3].max()

            merged_box = torch.tensor(
                [[x1, y1, x2, y2]],
                device=all_boxes.device,
                dtype=all_boxes.dtype
            )

        # -----------------------------------
        # SCORE MEAN
        # -----------------------------------

        merged_score = None

        if len(scores) > 0:

            all_scores = torch.cat(scores)

            merged_score = torch.tensor(
                [all_scores.float().mean()],
                device=all_scores.device,
                dtype=all_scores.dtype
            )

        return {
            "scores": merged_score,
            "labels": torch.tensor([1], device=self.device),
            "boxes": merged_box,
            "masks": merged_mask,
        }

    # =========================================================
    # DISPLAY
    # =========================================================

    def show(
        self,
        image : PILImage,
        results,
    ):
        """Render the evaluation output metrics and bounding items over the baseline image.

        Args:
            image (PIL.Image or numpy.ndarray):
                The original background target frame content.
            results (dict):
                The formatted bounding context layout to render onto the matrix canvas.

        """
        plot_results(image, results)
        plt.show()

    def process_prompt_dataset(
        self,
        image_path: str,
        prompts: list[dict],
    ):
        """Run SAM3 once with all prompts inside a single Datapoint, then split + filter per prompt after inference.

        Args:
            image_path (str):
                The disk coordinate target leading to the source image item file.
            prompts (List[dict]):
                A list of prompt configuration dictionaries tracking specific search bounds.

        Returns:
            A post-processed structure list grouping scores, filters, and sorted masks per query block.

        """
        dp = self.create_datapoint()
        image = PILImage.open(image_path).convert("RGB")
        self.set_image(dp, image)

        prompt_index = []

        # -----------------------------------
        # 1. BUILD SINGLE DATASET
        # -----------------------------------
        for p in prompts:

            if p.get("boxes") and len(p["boxes"]) > 0:
                self.add_visual_prompt(
                    dp,
                    boxes=p["boxes"],
                    labels=p["labels"],
                    text_prompt=p.get("prompt", "visual"),
                )
            else:
                self.add_text_prompt(dp, p.get("prompt", ""))

            prompt_index.append(p)

        # -----------------------------------
        # 2. SINGLE INFERENCE
        # -----------------------------------
        results = self.process([dp])

        # -----------------------------------
        # 3. SPLIT + FILTER PER PROMPT
        # -----------------------------------
        processed = []

        for p, (_, r) in zip(prompt_index, results.items()):

            threshold = float(p.get("threshold", 0.5))

            scores = r.get("scores")
            boxes = r.get("boxes")
            masks = r.get("masks")

            # -----------------------------------
            # NO RESULTS
            # -----------------------------------

            if scores is None or len(scores) == 0:
                processed.append({
                    "prompt": p["prompt"],
                    "scores": None,
                    "boxes": None,
                    "masks": None,
                })
                continue

            # -----------------------------------
            # NORMALIZE SHAPES
            # -----------------------------------

            scores = scores.view(-1)

            if boxes is not None:

                # force [N,4]
                if boxes.ndim == 3:
                    boxes = boxes.view(-1, 4)

                elif boxes.ndim == 1:
                    boxes = boxes.view(1, 4)

            if masks is not None:

                # force [N,1,H,W]
                if masks.ndim == 3:
                    masks = masks.unsqueeze(1)

                elif masks.ndim == 2:
                    masks = masks.unsqueeze(0).unsqueeze(0)

            # -----------------------------------
            # FILTER
            # -----------------------------------

            keep = scores >= threshold

            # sécurité
            keep_count = int(keep.sum().item())

            if keep_count == 0:
                processed.append({
                    "prompt": p["prompt"],
                    "scores": None,
                    "boxes": None,
                    "masks": None,
                })
                continue

            filtered_scores = scores[keep]

            filtered_boxes = (
                boxes[keep]
                if boxes is not None
                else None
            )

            filtered_masks = (
                masks[keep]
                if masks is not None
                else None
            )

            # -----------------------------------
            # SORT DESCENDING
            # -----------------------------------

            order = torch.argsort(
                filtered_scores,
                descending=True
            )

            filtered_scores = filtered_scores[order]

            if filtered_boxes is not None:
                filtered_boxes = filtered_boxes[order]

            if filtered_masks is not None:
                filtered_masks = filtered_masks[order]

            processed.append({
                "prompt": p["prompt"],
                "scores": filtered_scores,
                "boxes": filtered_boxes,
                "masks": filtered_masks,
            })

        return processed