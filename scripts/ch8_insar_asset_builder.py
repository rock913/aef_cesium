import ee
import os
import subprocess

def upload_insar_to_gee(velocity_tif, coherence_tif, asset_id):
    """
    将本地 MintPy 产出的高精度 InSAR 结果上传为 GEE Asset。
    """
    ee.Initialize()
    print(f"🚀 开始构建 InSAR GEE 资产: {asset_id}")

    # 1. 临时上传到 GCS (Google Cloud Storage)
    gcs_bucket = "gs://your-sros-bucket/insar_temp/"
    subprocess.run(f"gsutil cp {velocity_tif} {gcs_bucket}velocity.tif", shell=True, check=True)
    subprocess.run(f"gsutil cp {coherence_tif} {gcs_bucket}coherence.tif", shell=True, check=True)
    
    # 2. 从 GCS 导入到 GEE Asset，构建双波段 Image
    manifest = {
        "name": asset_id,
        "tilesets": [
            {"id": "velocity_tiles", "sources": [{"uris": [f"{gcs_bucket}velocity.tif"]}]},
            {"id": "coherence_tiles", "sources": [{"uris": [f"{gcs_bucket}coherence.tif"]}]}
        ],
        "bands": [
            {"id": "velocity", "tilesetId": "velocity_tiles", "missingData": {"values": [0]}},
            {"id": "coherence", "tilesetId": "coherence_tiles", "missingData": {"values": [0]}}
        ]
    }
    
    import json
    with open('manifest.json', 'w') as f:
        json.dump(manifest, f)
        
    print("⏳ 正在提交 GEE 云端构建任务...")
    subprocess.run("earthengine upload image --manifest manifest.json", shell=True)
    print("✅ 任务已提交！等待云端固化。")

if __name__ == "__main__":
    upload_insar_to_gee("./data/vel.tif", "./data/coh.tif", "projects/your_gee/assets/insar_gz_2020")
