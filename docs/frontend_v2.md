# Frontend UI/UX Refactor Specification: RAG Chat Interface
**Tech Stack:** React, Vite, Tailwind CSS, Lucide React (for icons)

## 1. Design Philosophy & Goal
Transform the current "terminal-style" full-width layout into a modern, centered, content-focused chat interface similar to **Perplexity AI** or **Claude**.
* **Theme:** Professional Dark Mode (Zinc/Slate palette).
* **Core Principle:** "Content Breathing Room." Text should never touch the edges of the screen.
* **Typography:** Clean sans-serif (Inter or system stack) with relaxed line heights.

## 2. Layout Structure (The "Shell")
The app should move away from the solid blue background.

* **Global Background:** `bg-zinc-950` (Very dark grey/black, not blue).
* **Text Color:** `text-zinc-100` for primary, `text-zinc-400` for secondary.
* **Main Container:**
    * Instead of full-width fluid text, use a centered column.
    * **Tailwind Class:** `max-w-3xl mx-auto w-full px-4`.
    * This ensures the eye doesn't have to travel 1900px across the screen.

## 3. Component Specifications

### A. The Header
* **Position:** Fixed top or Sticky.
* **Style:** Minimalist. Transparent with backdrop blur.
* **Elements:** App Logo/Name on the left, subtle settings/profile icon on the right.
* **Border:** `border-b border-white/5`.

### B. The Chat Area (Message List)
* **User Message:**
    * Align: Right or Distinct Background.
    * Style: `bg-zinc-800` text-white rounded-2xl rounded-tr-sm px-5 py-3.
    * Width: `max-w-[85%] ml-auto`.
* **AI Response (The RAG Output):**
    * Align: Left.
    * Style: No background bubble. Clean text directly on the canvas to encourage reading long documents.
    * **Typography:** `prose prose-invert prose-p:leading-relaxed prose-li:marker:text-zinc-400`.
    * **Markdown:** Must render Markdown properly (bold, lists, code blocks).

### C. The "Sources" Component (Crucial for RAG)
Instead of a text block at the bottom, use a "Sources Grid" immediately after the AI response but *before* the conclusion.

* **UI:** A horizontal row of cards or chips.
* **Card Style:**
    * `bg-zinc-900` border `border-zinc-800` hover:border-zinc-700 transition-colors.
    * `rounded-lg p-3 text-xs w-48 flex-shrink-0`.
    * **Icon:** Use a generic FileText icon (Lucide) + Truncated Title.
    * **Interaction:** Clicking opens a modal or new tab with the source content.

### D. The Input Area (Floating Bar)
Move away from the "BIOS footer" line.

* **Position:** Fixed at the bottom, centered.
* **Style:** A floating capsule, not a full-width bar.
* **Tailwind:** `w-full max-w-3xl mx-auto mb-6 bg-zinc-900/90 backdrop-blur border border-white/10 rounded-2xl shadow-2xl`.
* **Input Field:** Transparent textarea, no outline, resize-none.
* **Send Button:** A visually distinct icon button inside the capsule (right side).

## 4. Specific UX Improvements

### 1. Visual Hierarchy
* **Titles/Headers in Answer:** Use `text-zinc-200 font-semibold text-lg` (don't stick to default HTML sizes).
* **Loading State:**
    * Do not show a static "Loading..." text.
    * Use a **Skeleton Loader** or a "Streaming Text" effect (typewriter effect) if the backend supports it.

### 2. Spacing (Whitespace)
* Increase gap between messages: `space-y-8` in the message list container.
* Add padding to the bottom of the list so the last message isn't hidden behind the floating input bar (`pb-32`).

### 3. Scrollbar
* Customize the scrollbar to be thin and dark to match the theme.
    * `scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent`.

## 5. Suggested Tailwind Utility Classes (Reference)

```jsx
// Wrapper for the whole screen
<div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 font-sans antialiased selection:bg-indigo-500/30">

  {/* Header */}
  <header className="fixed top-0 w-full z-10 border-b border-white/5 bg-zinc-950/80 backdrop-blur-md">
     <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Content */}
     </div>
  </header>

  {/* Scrollable Chat Area */}
  <main className="flex-1 overflow-y-auto pt-20 pb-40">
    <div className="max-w-3xl mx-auto px-4 space-y-8">
       {/* Map your messages here */}
    </div>
  </main>

  {/* Input Area */}
  <div className="fixed bottom-0 w-full p-4 bg-gradient-to-t from-zinc-950 to-transparent pb-6">
    <div className="max-w-3xl mx-auto relative">
      <textarea 
        className="w-full bg-zinc-800/50 hover:bg-zinc-800 focus:bg-zinc-800 transition-colors border border-white/10 focus:border-indigo-500/50 rounded-2xl pl-4 pr-12 py-4 resize-none outline-none shadow-lg text-sm placeholder:text-zinc-500"
        rows={1}
        placeholder="Ask anything..."
      />
      <button className="absolute right-3 top-3 p-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white transition-all">
        {/* Send Icon */}
      </button>
    </div>
    <div className="text-center text-xs text-zinc-600 mt-2">
      AI generated content may be inaccurate.
    </div>
  </div>

</div>