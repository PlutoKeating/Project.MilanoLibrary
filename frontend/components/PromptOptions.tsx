import React from 'react'
import { UseFormReturn } from 'react-hook-form/dist/types/form'
import { PROMPT_LANGUAGE_MAP } from '~/utils/constants/language'

export function PromptOptions({ register, getValues }: { register: any; getValues: UseFormReturn['getValues'] }) {
  return (
    <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-3">
      <div>
        <label className="block font-mono text-xs text-slate-500">语言</label>
        <select
          className="mt-1 w-full border border-slate-700 bg-slate-900/50 px-2 py-1 font-mono text-xs text-slate-300 outline-none focus:border-cyan-500"
          {...register('outputLanguage')}
        >
          {Object.keys(PROMPT_LANGUAGE_MAP).map((k: string) => (
            <option key={PROMPT_LANGUAGE_MAP[k]} value={PROMPT_LANGUAGE_MAP[k]}>
              {k}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
