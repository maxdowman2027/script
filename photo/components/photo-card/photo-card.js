Component({
  properties: {
    item: { type: Object, value: {} },
    likeBusy: { type: Boolean, value: false }
  },
  data: {
    imgFailed: false
  },
  methods: {
    onOpen() {
      const item = this.data.item || {}
      this.triggerEvent('open', { photoId: item._id })
    },
    onLike(e) {
      this.triggerEvent('like', e.detail)
    },
    onImgError() {
      this.setData({ imgFailed: true })
    }
  }
})
