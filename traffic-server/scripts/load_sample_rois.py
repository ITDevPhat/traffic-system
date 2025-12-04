#!/usr/bin/env python3
"""
Script để load sample ROIs vào database
Usage: python scripts/load_sample_rois.py
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.models.roi import ROI
from sqlalchemy.orm import Session


def load_sample_rois(db: Session, json_file: str = "sample_rois.json"):
    """
    Load sample ROIs từ JSON file vào database
    
    Args:
        db: Database session
        json_file: Path to JSON file
    """
    # Read JSON file
    json_path = Path(__file__).parent.parent / json_file
    
    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    camera_id = data.get('camera_id', 'CAM_Q7_01')
    rois = data.get('rois', [])
    
    print(f"📦 Loading {len(rois)} ROIs for camera: {camera_id}")
    
    # Delete existing ROIs for this camera
    deleted = db.query(ROI).filter(ROI.camera_id == camera_id).delete()
    print(f"🗑️  Deleted {deleted} existing ROIs")
    
    # Insert new ROIs
    created_count = 0
    for roi_data in rois:
        try:
            roi = ROI(
                camera_id=camera_id,
                roi_type=roi_data['roi_type'],
                name=roi_data['name'],
                coordinates=roi_data['coordinates'],
                color=roi_data['color'],
                metadata=roi_data.get('metadata', {})
            )
            db.add(roi)
            created_count += 1
            print(f"  ✅ {roi_data['name']} ({roi_data['roi_type']})")
        except Exception as e:
            print(f"  ❌ Failed to create {roi_data.get('name', 'Unknown')}: {e}")
    
    db.commit()
    print(f"\n✅ Successfully loaded {created_count}/{len(rois)} ROIs")


def main():
    """Main function"""
    print("=" * 60)
    print("Load Sample ROIs Script")
    print("=" * 60)
    
    # Get database session
    db = next(get_db())
    
    try:
        load_sample_rois(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
