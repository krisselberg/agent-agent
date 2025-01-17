import requests
import json
import time

# Base URL for the API
BASE_URL = "http://localhost:8000"


def test_create_agent():
    print("\nTesting Create Agent endpoint...")
    url = f"{BASE_URL}/create_agent"
    payload = {
        # Add any required fields here
    }

    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")


def test_video_status():
    print("\nTesting Video Status endpoint...")
    # Using a dummy video ID
    video_id = "test_video_123"
    url = f"{BASE_URL}/video/{video_id}/status"

    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(
        f"Response: {response.json() if response.status_code == 200 else response.text}"
    )


def test_create_video():
    print("\nTesting Create Video endpoint...")
    url = f"{BASE_URL}/video"
    payload = {
        "video_id": "test_video_123",
        "character_ids": ["char1", "char2"],
        "description": "Test video description",
    }

    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")


def test_create_and_poll_video():
    print("\nTesting Create Video and Polling Status...")
    url = f"{BASE_URL}/video"
    payload = {
        "video_id": "test_video_123",
        "character_ids": ["char1", "char2"],
        "description": "Test video description",
    }

    # Create the video
    response = requests.post(url, json=payload)
    print(f"Create Video Status Code: {response.status_code}")
    print(f"Create Video Response: {response.json()}")

    if response.status_code == 201:
        video_id = payload["video_id"]
        print(f"\nPolling status for video {video_id}...")

        while True:
            status_response = requests.get(f"{BASE_URL}/video/{video_id}/status")
            status_data = (
                status_response.json()
                if status_response.status_code == 200
                else status_response.text
            )
            print(f"Status: {status_data}")

            # if isinstance(status_data, dict) and status_data.get("status") in [
            #     "completed",
            #     "failed",
            # ]:
            #     break

            time.sleep(0.5)


def main():
    print("Starting API Tests...")

    try:
        # Test all endpoints
        test_create_agent()
        test_create_and_poll_video()  # Replace individual tests with combined function

    except requests.exceptions.ConnectionError:
        print(
            "Error: Cannot connect to the server. Make sure the FastAPI server is running."
        )
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
