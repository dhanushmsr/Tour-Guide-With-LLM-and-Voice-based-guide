import cv2
import os
import numpy as np

class VisionEngine:
    def __init__(self):
        # Initialize ORB: Oriented FAST and Rotated BRIEF
        # nfeatures=2000 allows for high-detail detection on complex Dravidian architecture
        self.orb = cv2.ORB_create(nfeatures=2000)
        
        # FLANN parameters for ORB (using LSH index as ORB is binary)
        index_params = dict(algorithm=6, table_number=6, key_size=12, multi_probe_level=1)
        search_params = dict(checks=50)
        
        self.flann = cv2.FlannBasedMatcher(index_params, search_params)
        self.reference_dir = "static/reference_monuments/"
        
        if not os.path.exists(self.reference_dir):
            os.makedirs(self.reference_dir)

    def process_and_match(self, query_img_bytes):
        """Processes raw bytes and matches against reference library using geometric verification."""
        # Convert bytes to OpenCV format
        nparr = np.frombuffer(query_img_bytes, np.uint8)
        query_img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        if query_img is None:
            return None

        kp_query, des_query = self.orb.detectAndCompute(query_img, None)
        
        if des_query is None or len(kp_query) < 10:
            return None

        best_match_id = None
        max_verified_matches = 0

        # Iterate through reference library
        for filename in os.listdir(self.reference_dir):
            if not filename.lower().endswith((".jpg", ".png", ".jpeg")):
                continue
            
            ref_path = os.path.join(self.reference_dir, filename)
            ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
            
            if ref_img is None:
                continue

            kp_ref, des_ref = self.orb.detectAndCompute(ref_img, None)
            if des_ref is None or len(kp_ref) < 10:
                continue

            # KNN Matching
            try:
                matches = self.flann.knnMatch(des_query, des_ref, k=2)
            except:
                continue

            # Lowe's Ratio Test to find high-quality matches
            good_matches = []
            for m, n in matches:
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)

            # RANSAC Verification: Ensure the matched points form a valid geometric shape
            if len(good_matches) > 15:
                src_pts = np.float32([kp_query[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

                # Find Homography (Geometric alignment)
                _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if mask is not None:
                    verified_count = np.sum(mask)
                    if verified_count > max_verified_matches:
                        max_verified_matches = verified_count
                        best_match_id = os.path.splitext(filename)[0]

        # Threshold: Require at least 20 geometrically verified points for a successful ID
        return best_match_id if max_verified_matches > 20 else None

# --- EXTERNAL FUNCTION FOR API IMPORT ---
vision_service = VisionEngine()

def identify_landmark(image_bytes: bytes):
    """
    Called by app.api.recognition.
    Returns the filename (id) of the matched monument.
    """
    return vision_service.process_and_match(image_bytes)