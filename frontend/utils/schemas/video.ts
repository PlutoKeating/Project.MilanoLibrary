import { z } from 'zod'

export const videoConfigSchema = z.object({
  enableStream: z.boolean().optional(),
  model: z.string().optional(),
  showTimestamp: z.boolean().optional(),
  showEmoji: z.boolean().optional(),
  outputLanguage: z.string().optional(),
  useStructuredOutput: z.boolean().optional(),
  respectChapters: z.boolean().optional(),
  modelType: z.enum(['online', 'local']).optional(),
  localModel: z.string().optional(),
})

export type VideoConfigSchema = z.infer<typeof videoConfigSchema>
