export enum VideoService {
  Bilibili = 'bilibili',
  Youtube = 'youtube',
  LocalVideo = 'local-video',
}

export interface LocalModel {
  name: string
  label: string
  size: string
  installed: boolean
}
