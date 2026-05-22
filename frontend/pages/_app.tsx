import type { AppProps } from 'next/app'
import React from 'react'
import Header from '../components/Header'
import Footer from '../components/Footer'
import '../styles/globals.css'
import '../styles/markdown.css'

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <div className="mx-auto flex min-h-screen flex-col bg-[#0a0a0f] font-mono text-slate-200">
      <Header />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center">
        <Component {...pageProps} />
      </main>
      <Footer />
    </div>
  )
}

export default MyApp
