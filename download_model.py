from huggingface_hub import hf_hub_download
hf_hub_download(repo_id="imageomics/Drexel-metadata-generator", filename="model_final.pth", local_dir="./output/enhanced")