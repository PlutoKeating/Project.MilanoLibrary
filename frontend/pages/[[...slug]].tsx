import { zodResolver } from '@hookform/resolvers/zod'
import getVideoId from 'get-video-id'
import type { NextPage } from 'next'
import { useRouter } from 'next/router'
import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import { SubmitHandler, useForm } from 'react-hook-form'
import useFormPersist from 'react-hook-form-persist'
import { AdapterManager } from '~/components/AdapterManager'
import { ModelSelector } from '~/components/ModelSelector'
import { PromptOptions } from '~/components/PromptOptions'
import { SubmitButton } from '~/components/SubmitButton'
import { SummaryResult } from '~/components/SummaryResult'
import { TimelineProgress } from '~/components/TimelineProgress'
import { UserKeyInput } from '~/components/UserKeyInput'
import { useClearCache } from '~/hooks/useClearCache'
import { useLocalStorage } from '~/hooks/useLocalStorage'
import { useModelManager } from '~/hooks/useModelManager'
import { useSummarize } from '~/hooks/useSummarize'
import { VideoService } from '~/lib/types'
import { DEFAULT_LANGUAGE } from '~/utils/constants/language'
import { extractPage, extractUrl } from '~/utils/extractUrl'
import { getVideoIdFromUrl } from '~/utils/getVideoIdFromUrl'
import { VideoConfigSchema, videoConfigSchema } from '~/utils/schemas/video'

export const Home: NextPage = () => {
  const router = useRouter()
  const urlState = router.query.slug
  const searchParams = useMemo(() => {
    const [, queryString = ''] = router.asPath.split('?')
    return new URLSearchParams(queryString)
  }, [router.asPath])

  const { register, handleSubmit, getValues, watch, setValue } = useForm<VideoConfigSchema>({
    defaultValues: {
      enableStream: true,
      model: '',
      showTimestamp: false,
      showEmoji: true,
      outputLanguage: DEFAULT_LANGUAGE,
      useStructuredOutput: true,
      respectChapters: true,
      modelType: 'online',
      localModel: 'small',
    },
    resolver: zodResolver(videoConfigSchema),
  })

  const [currentVideoId, setCurrentVideoId] = useState<string>('')
  const [currentVideoUrl, setCurrentVideoUrl] = useState<string>('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [userKey, setUserKey] = useLocalStorage<string>('user-openai-apikey')
  const [userBaseUrl, setUserBaseUrl] = useLocalStorage<string>('user-openai-base-url')
  const [userModelName, setUserModelName] = useLocalStorage<string>('user-openai-model')
  const [backendBaseUrl, setBackendBaseUrl] = useLocalStorage<string>('backend-base-url')
  const { loading, summary, taskStatus, resetSummary, summarize, uploadAndSummarize } = useSummarize()
  const { loading: clearingCache, clearCache, message: cacheMessage } = useClearCache()
  const { models, statusMap, startDownload } = useModelManager()
  const [selectedAdapterId, setSelectedAdapterId] = useState<string>('bilibili')

  const fileInputRef = useRef<HTMLInputElement>(null)

  useFormPersist('video-summary-config-storage', {
    watch,
    setValue,
    storage: typeof window !== 'undefined' ? window.localStorage : undefined,
  })
  const shouldShowTimestamp = getValues('showTimestamp')

  useEffect(() => {
    const validatedUrl = getVideoIdFromUrl(router.isReady, currentVideoUrl, urlState, searchParams)
    validatedUrl && generateSummary(validatedUrl)
  }, [router.isReady, urlState, searchParams])

  const validateUrlFromAddressBar = useCallback(
    (url?: string) => {
      const videoUrl = url || currentVideoUrl
      if (!videoUrl) return false

      if (['bilibili', 'youtube'].includes(selectedAdapterId)) {
        if (!(videoUrl.includes('bilibili.com') || videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be'))) {
          return false
        }
      }
      if (url) {
        setCurrentVideoUrl(videoUrl)
      }
      return true
    },
    [currentVideoUrl, selectedAdapterId],
  )

  const generateSummary = async (url?: string) => {
    const formValues = getValues()
    resetSummary()
    const valid = validateUrlFromAddressBar(url)
    if (!valid) return

    const videoUrl = url || currentVideoUrl
    const pageNumber = extractPage(videoUrl, searchParams)

    setCurrentVideoId(videoUrl)
    await summarize(
      { videoId: videoUrl, service: selectedAdapterId, pageNumber, ...formValues },
      { userKey, baseUrl: userBaseUrl, modelName: userModelName, shouldShowTimestamp: shouldShowTimestamp },
    )

    setTimeout(() => {
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
    }, 10)
  }

  const onFormSubmit: SubmitHandler<VideoConfigSchema> = async () => {
    if (uploadFile) {
      resetSummary()
      setCurrentVideoId(uploadFile.name)
      setCurrentVideoUrl('')
      const formValues = getValues()
      await uploadAndSummarize(
        uploadFile,
        { service: VideoService.LocalVideo, ...formValues },
        { userKey, baseUrl: userBaseUrl, modelName: userModelName, shouldShowTimestamp },
      )
      setTimeout(() => {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
      }, 10)
      return
    }

    await generateSummary(currentVideoUrl)
  }

  const handleApiKeyChange = (e: any) => setUserKey(e.target.value)
  const handleBaseUrlChange = (e: any) => setUserBaseUrl(e.target.value)
  const handleModelNameChange = (e: any) => setUserModelName(e.target.value)
  const handleBackendBaseUrlChange = (e: any) => setBackendBaseUrl(e.target.value)
  const handleInputChange = (e: any) => setCurrentVideoUrl(e.target.value)
  const handleModelTypeChange = (type: 'online' | 'local') => setValue('modelType', type)
  const handleLocalModelChange = (name: string) => setValue('localModel', name)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setUploadFile(file)
  }

  const handleRemoveFile = () => {
    setUploadFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="w-full px-4 pt-16 lg:px-0">
      <div className={`mx-auto transition-all duration-300 ${summary ? 'max-w-5xl' : 'max-w-3xl'}`}>
        <div className="mx-auto max-w-3xl">
          <h1 className="text-center font-mono text-2xl font-bold tracking-wider text-cyan-400 sm:text-4xl">MILANO LIBRARY</h1>
          <p className="mt-2 text-center font-mono text-xs tracking-widest text-fuchsia-400">
            VIDEO INTELLIGENCE // AI SUMMARY
          </p>

        <UserKeyInput
          value={userKey}
          onChange={handleApiKeyChange}
          baseUrl={userBaseUrl}
          onBaseUrlChange={handleBaseUrlChange}
          modelName={userModelName}
          onModelNameChange={handleModelNameChange}
          backendBaseUrl={backendBaseUrl}
          onBackendBaseUrlChange={handleBackendBaseUrlChange}
        />

        <form onSubmit={handleSubmit(onFormSubmit)} className="mt-8">
          <input
            type="text"
            value={currentVideoUrl}
            onChange={handleInputChange}
            disabled={!!uploadFile || loading}
            className="w-full border border-slate-700 bg-slate-900/50 px-4 py-3 font-mono text-sm text-cyan-100 placeholder-slate-500 outline-none focus:border-cyan-500 disabled:opacity-50"
            placeholder="输入视频链接"
          />

          <AdapterManager
            selectedAdapterId={selectedAdapterId}
            onSelectAdapter={setSelectedAdapterId}
          />

          <div className="mt-4">
            {!uploadFile ? (
              <label className="flex cursor-pointer items-center justify-center border border-dashed border-slate-700 bg-slate-900/30 px-4 py-6 font-mono text-xs tracking-wider text-slate-400 hover:border-cyan-500 hover:text-cyan-400">
                <span>上传本地视频文件</span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  disabled={loading}
                  className="hidden"
                />
              </label>
            ) : (
              <div className="flex items-center justify-between border border-slate-700 bg-slate-900/30 px-4 py-3">
                <span className="font-mono text-xs text-cyan-100">{uploadFile.name}</span>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  disabled={loading}
                  className="font-mono text-xs text-slate-400 hover:text-fuchsia-400 disabled:opacity-50"
                >
                  移除
                </button>
              </div>
            )}
          </div>

          <div className="mt-6 flex gap-4">
            <SubmitButton loading={loading} />
            <button
              type="button"
              onClick={clearCache}
              disabled={clearingCache || loading}
              className="shrink-0 border border-slate-700 bg-transparent px-6 py-3 font-mono text-xs tracking-wider text-slate-400 hover:border-cyan-500 hover:text-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {clearingCache ? 'CLEARING...' : 'CLEAR CACHE'}
            </button>
          </div>

          {cacheMessage && (
            <p className="mt-2 font-mono text-xs text-fuchsia-400">{cacheMessage}</p>
          )}

          <ModelSelector
            modelType={watch('modelType') || 'online'}
            selectedLocalModel={watch('localModel') || 'small'}
            models={models}
            statusMap={statusMap}
            onModelTypeChange={handleModelTypeChange}
            onLocalModelChange={handleLocalModelChange}
            onDownload={startDownload}
          />

          <PromptOptions getValues={getValues} register={register} />
        </form>

        {(loading || taskStatus) && (
          <TimelineProgress taskStatus={taskStatus} />
        )}
      </div>

      {summary && (
        <SummaryResult
          summary={summary}
          currentVideoUrl={currentVideoUrl}
          currentVideoId={currentVideoId}
          shouldShowTimestamp={shouldShowTimestamp}
        />
      )}
    </div>
  </div>
  )
}

export default Home
