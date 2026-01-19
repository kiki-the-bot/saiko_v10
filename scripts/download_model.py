import os
from huggingface_hub import snapshot_download

# Define the exact model you are using
# (Change this to the specific repo you downloaded from, e.g., turboderp or whoever)
REPO_ID = "turboderp/Mistral-Nemo-12B-exl2-4.5bpw" 

# Where to save it relative to this script
MODEL_DIR = os.path.join(os.getcwd(), "models", "mistral_nemo")

def download_brain():
    print(f"🧠 SAIKO INSTALLER: Checking for Brain...")
    
    if os.path.exists(os.path.join(MODEL_DIR, "model.safetensors.index.json")):
        print(f"✅ Brain already detected at: {MODEL_DIR}")
        return

    print(f"⬇️ Brain missing. Downloading {REPO_ID} from HuggingFace...")
    print("☕ Grab a coffee. This is 8GB+.")
    
    try:
        snapshot_download(
            repo_id=REPO_ID, 
            local_dir=MODEL_DIR, 
            local_dir_use_symlinks=False
        )
        print("✅ Download Complete.")
    except Exception as e:
        print(f"❌ Download Failed: {e}")
        print("You might need to install: pip install huggingface_hub")

if __name__ == "__main__":
    download_brain()