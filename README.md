# NodeSeek-Signin

NodeSeek论坛签到，借助github action 自动触发，默认选择随机签到

需要自行在 setting 中添加 Repository secrets

|  名称  |                        含义                         |
| :----: | :-------------------------------------------------: |
| COOKIE | 论坛用户cookie，需含 session（建议连同 cf_clearance），自行在浏览器F12中查看 |

运行结果看 Actions 日志：

- `今天的签到收益是x个鸡腿` → 签到成功
- `USER NOT FOUND` → cookie 失效，重新抓取后更新 `COOKIE`
- 网络异常 / 5xx / Cloudflare 挑战页会重试 3 次，仍然失败则退出码 1
