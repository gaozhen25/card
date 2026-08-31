const app = getApp()

Page({
  data: {
    wechatId: '你的微信号',
    wechatQrcode: '/images/qrcode.jpg'
  },

  onLoad() {
    this.setData({
      wechatId: app.globalData.wechatId,
      wechatQrcode: app.globalData.wechatQrcode
    })
  },

  // 复制微信号
  copyWechatId() {
    wx.setClipboardData({
      data: this.data.wechatId,
      success() {
        wx.showToast({
          title: '微信号已复制',
          icon: 'success'
        })
      }
    })
  },

  // 预览二维码（长按识别）
  previewQrcode() {
    wx.previewImage({
      urls: [this.data.wechatQrcode],
      current: this.data.wechatQrcode
    })
  },

  // 保存二维码到相册
  saveQrcode() {
    wx.saveImageToPhotosAlbum({
      filePath: this.data.wechatQrcode,
      success() {
        wx.showToast({
          title: '已保存到相册',
          icon: 'success'
        })
      },
      fail() {
        wx.showToast({
          title: '保存失败，请长按图片保存',
          icon: 'none'
        })
      }
    })
  }
})
