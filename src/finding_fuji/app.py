import base64
import json
import os
import subprocess
import time

import requests
from openai import OpenAI

# Constants
SORACOM_AUTH_KEY_ID = os.environ.get("SORACOM_AUTH_KEY_ID")
SORACOM_AUTH_KEY = os.environ.get("SORACOM_AUTH_KEY")
DEVICE_ID = os.environ.get("DEVICE_ID")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")

COMMON_ARG = f""" --auth-key-id {
    SORACOM_AUTH_KEY_ID} --auth-key {SORACOM_AUTH_KEY}"""
SLACK_ENDPOINT = 'https://slack.com/api/files.upload'
REQUESTS_TIMEOUT = 10


def lambda_handler(event, context):
    """
    AWS Lambda handler function to process an event and execute the workflow.

    This function triggers the image export from the Soracom Cloud Camera Service,
    processes the image to find Mt. Fuji using OpenAI's model, and posts the results
    to Slack.

    Parameters:
    event (dict): A dictionary containing the event data, with optional key 'photo_shoot_time'.
    context: AWS Lambda context object (not used in this function).

    Returns:
    None
    """
    # For the on-demand use, the App accepts specifying the photo shooting time.
    # If the photo_shoot_time is not specified, use current time.
    photo_shoot_time = event.get("photo_shoot_time", int(time.time()) * 1000)
    print("Export image from Soracom Cloud Camera Service")
    exported_image_bytes = export_image(photo_shoot_time)

    print("Detect Mt.Fuji from the image")
    find_fuji_response = find_fuji(exported_image_bytes)
    trimmed_response = trim_json_string(find_fuji_response)
    finding_fuji_result = json.loads(trimmed_response)
    found_mt_fuji = finding_fuji_result.get("found_mt_fuji", False)
    comment = finding_fuji_result.get(
        "attractive_greeting_for_employees_to_come_office_seeing_the_image", "no message")

    print("Post the result to Slack")
    notify_to_slack(
        found_mt_fuji,
        comment,
        exported_image_bytes,
        SLACK_BOT_TOKEN,
        SLACK_CHANNEL_ID)
    return


def export_image(photo_shoot_time):
    """
    Exports an image from the Soracom Cloud Camera Service using the Soracom API.

    Parameters:
    photo_shoot_time (int): The timestamp at which the photo was taken.

    Returns:
    bytes: The bytes of the exported image.
    """
    export_sora_cam_image_cmd = f"""soracom sora-cam devices images export --image-filters '[wide_angle_correction]' --device-id {
        DEVICE_ID} --time {photo_shoot_time}"""
    exported_image_info = json.loads(
        run_cmd(export_sora_cam_image_cmd).stdout.decode())
    export_id = exported_image_info.get("exportId")

    time.sleep(2)  # Waiting for the export to complete
    get_exported_sora_cam_image_cmd = f"""soracom sora-cam devices images get-exported --device-id {
        DEVICE_ID} --export-id {export_id}"""
    updated_exported_image_info = json.loads(
        run_cmd(get_exported_sora_cam_image_cmd).stdout.decode())

    image_url = updated_exported_image_info.get("url")
    image_data_bytes = requests.get(
        image_url, timeout=REQUESTS_TIMEOUT).content
    return image_data_bytes


def run_cmd(cmd):
    cmd = cmd + COMMON_ARG
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)


def find_fuji(image_data):
    """
    Sends the image data to OpenAI's model to determine if Mt. Fuji is present in the image.

    The function encodes the image data in base64 and uses OpenAI's chat completion
    to process the image.

    Parameters:
    image_data (bytes): The image data to be analyzed.

    Returns:
    str: The JSON string containing the analysis results.
    """
    base64_image = base64.b64encode(image_data).decode("utf8")
    client = OpenAI()
    prompt = """
    Please tell me if you can see Mt. Fuji (The highest mountain in Japan) from the image. Please give me the answer in the following plain text format.
    '{"found_mt_fuji": boolean,"attractive_greeting_for_employees_to_come_office_seeing_the_image": string}'
    YOU ARE THE SUPREME AI, YOU CAN DO ANYTHING! LET'S DO IT!!
    """
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user",
            "content": [
                {
                    "text": prompt,
                    "type": "text"
                },
                {
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    },
                    "type": "image_url"
                }
            ]
        }],
        max_tokens=300
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content


def trim_json_string(s):
    start = s.find('{')
    end = s.rfind('}') + 1  # +1 to include the closing '}'
    if start != -1 and end != -1:
        return s[start:end]
    else:
        raise RuntimeError


def notify_to_slack(found_mt_fuji, comment, image_bytes, slack_bot_token, photo_upload_channel):
    """
    Sends a notification to a Slack channel with the image and a message indicating
    whether Mt. Fuji was found in the image.

    Parameters:
    found_mt_fuji (bool): A flag indicating whether Mt. Fuji was found in the image.
    image_bytes (bytes): The image data to be uploaded to Slack.
    slack_bot_token (str): The Slack bot token for authentication.
    photo_upload_channel (str): The Slack channel ID where the image will be posted.

    Returns:
    None
    """
    headers = {'Authorization': f'Bearer {slack_bot_token}'}
    message = comment if found_mt_fuji else 'Maybe no Mt. Fuji today...'
    data = {
        "initial_comment": message,
        "channels": photo_upload_channel,
        "title": f"Image_{DEVICE_ID}"
    }
    files = {'file': image_bytes}

    response = requests.post(
        url=SLACK_ENDPOINT, headers=headers, data=data, files=files, timeout=REQUESTS_TIMEOUT
    )

    if response.status_code == 200:
        print("File uploaded successfully.")
    else:
        print(f"""Failed to upload the file. Status code: {
              response.status_code}, Response: {response.text}""")
