App({
  onLaunch() {
    console.log('小程序启动')
  },
  globalData: {
    wechatId: '你的微信号', // 替换成你的微信号
    wechatQrcode: '/images/qrcode.jpg' // 替换成你的微信二维码图片路径
  }
})
