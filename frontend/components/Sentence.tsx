import { extractSentenceWithTimestamp, extractTimestamp, trimSeconds } from '~/utils/summary'

export default function videoIdSentence({
  videoId,
  videoUrl,
  sentence,
}: {
  videoId: string
  videoUrl: string
  sentence: string
}) {
  const isBiliBili = videoUrl.includes('bilibili.com')
  const baseUrl = isBiliBili
    ? `https://www.bilibili.com/video/${videoId}/?t=`
    : `https://youtube.com/watch?v=${videoId}&t=`

  const matchResult = extractSentenceWithTimestamp(sentence)
  if (matchResult) {
    const secondsStr = matchResult[1].split(':')[0]
    const seconds = trimSeconds(secondsStr)
    const { formattedContent, timestamp } = extractTimestamp(matchResult)

    return (
      <div className="font-mono text-sm">
        <a
          href={`${encodeURI(baseUrl + seconds)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyan-400 hover:text-cyan-300"
        >
          [{timestamp}]
        </a>
        <span className="ml-2 text-slate-300">{formattedContent}</span>
      </div>
    )
  }
  return <div className="font-mono text-sm text-slate-300">{sentence}</div>
}
