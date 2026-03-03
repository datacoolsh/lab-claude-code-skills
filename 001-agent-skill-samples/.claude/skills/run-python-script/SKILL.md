---
name: run-python-script
description: 当发送消息时触发这个函数，并返回响应
---

## 输入参数
参数：MESSAGE_TEMPLATE = "我要测试这条消息"

## 返回参数
执行成功时返回状态消息
例如：
```json
{"statusCode": 200, "body": "OK"}
```
## 执行脚本
执行脚本: `python -m ./hello.py`


