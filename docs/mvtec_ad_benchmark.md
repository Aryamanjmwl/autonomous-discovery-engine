# MVTec AD local benchmark qualification

ADE supports local research evaluation with one category from the classic
[MVTec AD dataset](https://www.mvtec.com/research-teaching/datasets/mvtec-ad).
The dataset contains defect-free training images and labeled normal/anomalous
test images with pixel masks across industrial object and texture categories.

MVTec releases the data under CC BY-NC-SA 4.0. Commercial use is not allowed.
ADE does not download, redistribute, or commit the dataset. Download it from the
official source, review its current terms, and keep the extracted files outside
this repository.

## Expected local layout

Qualify one category at a time. For example, the `bottle` category must contain:

```text
<dataset-root>/
  bottle/
    train/
      good/
        *.png
    test/
      good/
        *.png
      <anomaly-type>/
        *.png
    ground_truth/
      <anomaly-type>/
        <test-image-stem>_mask.png
```

The qualifier requires at least one reference image, one normal test image, one
anomaly directory, and one matching mask for every anomaly image. It rejects
unsafe category paths, missing directories, missing masks, duplicate manifest
content, and attempts to replace a different existing manifest.

## 1. Qualify a category

From the ADE repository in PowerShell:

```powershell
python -m ade.cli `
  --qualify-mvtec-ad "D:\Datasets\mvtec_anomaly_detection" `
  --mvtec-category bottle `
  --mvtec-dataset-version classic `
  --benchmark-manifest-output "data\benchmarks\mvtec_ad\bottle.json"
```

The command prints the exact defect-free reference directory, image counts, a
SHA-256 fingerprint of the declared test images and masks, the canonical
manifest path, and the non-commercial license warning.

The manifest stores absolute local paths, per-file SHA-256 values, labels,
anomaly types, mask paths, source URL, and license metadata. Repeating the
command with unchanged data is idempotent. If files change, write a new manifest
path or intentionally archive the earlier manifest before replacement.

## 2. Build reference memory

Use the printed `train/good` directory:

```powershell
python -m ade.cli `
  --build-reference-memory "D:\Datasets\mvtec_anomaly_detection\bottle\train\good" `
  --reference-memory-output "data\reference_memory\mvtec_ad\bottle" `
  --config "configs\reference_build.yaml"
```

Record the immutable manifest path printed by this command in a dedicated
reference-scoring configuration. Patch extraction and representation settings
must match between memory construction and benchmark execution.

## 3. Declare evaluation policy before test evaluation

Before running the held-out `test` split, choose and record minimum AUROC and
average precision, required precision and recall at a declared operating point,
maximum review fraction, maximum missing predictions, and the exact dataset
name, version, and split.

Do not choose thresholds after inspecting test labels or scores. The repository's
controlled synthetic fixture checks software behavior only and is not a
performance baseline.

## 4. Execute and preserve the baseline

Use `run_reference_benchmark` with the qualified manifest, the compatible
reference-scoring configuration, and a `VisualBenchmarkRunConfig`. Apply
`evaluate_visual_benchmark_acceptance` with the predeclared policy, then publish
the benchmark result through `publish_visual_benchmark_artifact`.

Run categories independently. Do not combine category scores into one claim
without a separately justified aggregation method. Image-level AUROC and
average precision do not measure pixel-mask localization quality; ADE currently
retains mask provenance but does not yet compute pixel-level segmentation
metrics.

All results remain Technical Preview validation evidence. They are not product
guarantees or automatic industrial inspection decisions.
