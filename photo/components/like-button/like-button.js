Component({
  options: {
    virtualHost: true
  },
  properties: {
    liked: { type: Boolean, value: false },
    likeCount: { type: Number, value: 0 },
    busy: { type: Boolean, value: false },
    photoId: { type: String, value: '' }
  },
  methods: {
    onTap() {
      if (this.data.busy) return
      this.triggerEvent('toggle', {
        photoId: this.data.photoId,
        liked: this.data.liked,
        likeCount: this.data.likeCount
      })
    }
  }
})
