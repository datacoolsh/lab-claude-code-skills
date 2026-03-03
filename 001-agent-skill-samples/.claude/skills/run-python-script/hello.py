MESSAGE_TEMPLATE = "Hello, 测试一条消息！"


def send_message(message: str):
    print(message)
    return {"statusCode": 200, "body": "OK"}


if __name__ == "__main__":
    send_message(MESSAGE_TEMPLATE)
