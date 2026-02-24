import os
import json

def get_edge_profiles():
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    edge_user_data = os.path.join(local_app_data, "Microsoft", "Edge", "User Data")
    
    if not os.path.exists(edge_user_data):
        print(f"Edge User Data directory not found at: {edge_user_data}")
        return

    print(f"Checking Edge User Data at: {edge_user_data}")
    
    # Check for "Local State" file which contains profile info
    local_state_path = os.path.join(edge_user_data, "Local State")
    if os.path.exists(local_state_path):
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                profiles = data.get("profile", {}).get("info_cache", {})
                
                print("\nFound the following Edge profiles:")
                print("-" * 50)
                print(f"{'Profile Name (In Browser)':<30} | {'Folder Name (Use in config)':<30}")
                print("-" * 50)
                
                for folder_name, info in profiles.items():
                    profile_name = info.get("name", "Unknown")
                    print(f"{profile_name:<30} | {folder_name:<30}")
                    
                print("-" * 50)
                return
        except Exception as e:
            print(f"Error reading Local State file: {e}")

    # Fallback: List directories if Local State reading fails
    print("\nCould not read profile names from Local State. Listing potential profile directories:")
    for item in os.listdir(edge_user_data):
        item_path = os.path.join(edge_user_data, item)
        if os.path.isdir(item_path):
            if item == "Default" or item.startswith("Profile"):
                print(f" - {item}")

if __name__ == "__main__":
    get_edge_profiles()
