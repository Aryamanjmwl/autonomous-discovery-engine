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

The qualifier accepts only the 15 official classic category names and requires
at least one reference image, one normal test image, one anomaly directory, and
one matching mask for every anomaly image. It rejects
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

Qualification proves that the selected local files follow the expected layout
and fixes their content identity. It does not prove that the files came from the
official archive; retain your original download record separately.

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

Before running the held-out `test` split, create a versioned JSON policy with
the exact dataset name, version, and split. Choose minimum ranking metrics,
required precision and recall at declared operating points, maximum review
fraction, and maximum missing predictions before inspecting test labels or
scores.

This example is illustrative configuration, not an ADE performance claim or a
recommended production threshold:

```json
{
  "schema_version": 1,
  "dataset_name": "mvtec-ad-bottle",
  "dataset_version": "classic",
  "split_name": "test",
  "min_auroc": 0.8,
  "min_average_precision": 0.8,
  "max_missing_predictions": 0,
  "operating_points": [
    {
      "strategy": "top_k",
      "value": 10,
      "min_precision": 0.5,
      "min_recall": null,
      "max_selected_fraction": 0.2
    }
  ]
}
```

Save the policy outside generated artifact directories, review it, and commit it
only if its dataset-bound requirements are justified for the experiment. ADE
derives the benchmark run configuration from these operating points, preventing
the command from measuring a different set of gates than the policy declares.
The repository's controlled synthetic fixture checks software behavior only and
is not a performance baseline.

## 4. Execute and preserve the baseline

Run the qualified manifest with the compatible reference-scoring configuration
and the predeclared policy:

```powershell
python -m ade.cli `
  --run-reference-benchmark "data\benchmarks\mvtec_ad\bottle.json" `
  --config "configs\mvtec_ad_bottle_reference.yaml" `
  --benchmark-policy "configs\benchmarks\mvtec_ad_bottle_policy.json" `
  --benchmark-output-root "data\benchmarks\reference_baselines"
```

The command prints the dataset identity, scoring ID, reference-memory ID,
image-level AUROC and average precision, acceptance decision, and immutable
artifact path. The content-addressed artifact contains the full benchmark
result, scorer provenance, exact policy, checks, failures, limitations, and
human-review requirement.

A failed gate is still published as evidence and then exits with status code
`2`, making the command suitable for a CI or experiment gate without discarding
the failed result. Invalid inputs or artifacts use the normal CLI error path.

Run categories independently. Do not combine category scores into one claim
without a separately justified aggregation method. Image-level AUROC and
average precision do not measure pixel-mask localization quality; ADE currently
retains mask provenance but does not yet compute pixel-level segmentation
metrics.

All results remain Technical Preview validation evidence. They are not product
guarantees or automatic industrial inspection decisions.
