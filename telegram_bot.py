# -*- coding: utf-8 -*-
import os
import pickle
from typing import Dict, Iterable, List, Optional

from dotenv import get_key
from httpx import Response, get, post

DOTENV_PATH: str = ".env"
TOKEN: str = get_key(DOTENV_PATH, "TOKEN")
SUBSCRIBERS_FILE: str = "subscribers.pickle"
BASE_URL: str = f"https://api.telegram.org/bot{TOKEN}"


def get_updates() -> Optional[Dict]:
    url: str = f"{BASE_URL}/getUpdates"
    response: Response = post(url)
    response_body: Dict = response.json()
    if not response_body["ok"]:
        raise Exception("Failed to fetch updates")
    return response_body


def get_filtered_messages(response_body: Dict, type: str) -> Iterable[Dict]:
    return filter(lambda update: type in update["message"], response_body["result"])


def update_subscribers() -> List:
    updates: Dict = get_updates()
    messages: List[Dict] = get_filtered_messages(updates, "text")
    fetched_subscribers = [
        update["message"]["chat"]["id"]
        for update in filter(
            lambda update: update["message"]["text"] == "/start", messages
        )
    ]
    with open(SUBSCRIBERS_FILE, "rb") as file:
        old_subscribers: List[int] = pickle.load(file)
        new_subscribers: List[int] = list(
            filter(lambda chat_id: chat_id not in old_subscribers, fetched_subscribers)
        )
        old_subscribers.extend(new_subscribers)
        for chat_id in new_subscribers:
            message: str = "Welcome to the Crome Detector Bot!"
            url: str = f"{BASE_URL}/sendMessage"
            query_parameters = {"chat_id": chat_id, "text": message}
            response: Response = get(url, params=query_parameters)
            response_body: Dict = response.json()
            if not response_body["ok"]:
                raise Exception(
                    f"Failed to send message `{message}` to chat `{chat_id}`"
                )
    with open(SUBSCRIBERS_FILE, "wb") as file:
        pickle.dump(list(old_subscribers), file)
    return old_subscribers


def load_subscribers() -> List[int]:
    if not os.path.exists(SUBSCRIBERS_FILE):
        raise Exception("Subscribers file not found!")
    with open(SUBSCRIBERS_FILE, "rb") as file:
        subscribers: List[int] = pickle.load(file)
    return subscribers


def send_message(message: str) -> None:
    """Function to send a plaintext message"""
    url: str = f"{BASE_URL}/sendMessage"
    subscribers: List[int] = load_subscribers()
    for chat_id in subscribers:
        query_parameters: Dict = {"chat_id": chat_id, "text": message}
        response: Response = get(url, params=query_parameters)
        response_body: Dict = response.json()
        if not response_body["ok"]:
            raise Exception(f"Failed to send message `{message}` to chat `{chat_id}`")
        print(f"Sent to chat {chat_id}")


def send_video(video: str, spoiler: bool = True) -> None:
    """Function to send a video message"""
    url: str = f"{BASE_URL}/sendVideo"
    subscribers: List[int] = load_subscribers()
    with open(video, "rb") as file:
        for chat_id in subscribers:
            files: Dict = {"video": file}
            request_body: Dict = {
                "chat_id": chat_id,
                "has_spoiler": spoiler,
                "caption": "Here's the video!",
            }
            response: Response = post(url, data=request_body, files=files)
            response_body: Dict = response.json()
            if not response_body["ok"]:
                raise Exception(f"Failed to send video `{video}` to `{chat_id}`")
            print(f"Sent to chat {chat_id}")


def main() -> None:
    print("1 - Send message")
    print("2 - Send video")
    option: int = int(input("Enter an option: "))
    if option == 1:
        message: str = input("Enter the message to send: ")
        send_message(message)
    elif option == 2:
        video: str = input("Enter the video path: ")
        send_video(video)


if __name__ == "__main__":
    main()
