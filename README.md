# 将微信读书划线和笔记同步到Readwise


本项目通过Github Action每天定时同步微信读书划线到Readwise。


## 使用

1. star本项目
2. fork这个工程
3. 获取微信读书的Cookie
    * 浏览器打开 https://weread.qq.com/
    * 按F12进入开发者模式，微信扫码登录确认，提示没有权限忽略即可
    * 依次点 Network -> Doc -> Headers-> cookie。找到weread.qq.com的网页，然后右侧寻找，最后复制 Cookie 字符串;
4. 获取ReadwiseToken
    * 浏览器打开 https://readwise.io/access_token
    * 点击get access，然后copy
5. 在Github的Secrets中添加以下变量
    * 打开你fork的工程，点击Settings->Secrets and variables->New repository secret
    * Secrets选项下添加以下变量,不需要加引号
        * WEREAD_COOKIE
        * READWISE_TOKEN
6. 回到Actions，开启Workflow权限，手动测试运行成功，即可自动每天更新


