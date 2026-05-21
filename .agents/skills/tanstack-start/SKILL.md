---
name: tanstack-start
description: TanStack Start routing patterns for this project. Use when creating or editing files in src/routes/, implementing navigation with Link or useNavigate, protecting routes, or working with route parameters and loaders.
---

# TanStack Start Skill

TanStack Start — file-based routing поверх TanStack Router. Каждый файл в `src/routes/` = один маршрут.

## Обязательная структура файла роута

```tsx
// src/routes/index.tsx        → "/"
// src/routes/settings.tsx     → "/settings"
// src/routes/track/$trackId.tsx → "/track/:trackId"
// src/routes/__root.tsx       → корневой layout

// ✅ обязательный экспорт Route
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/")({
  component: HomePage,
})

function HomePage() {
  return <div>Home</div>
}

// ❌ TanStack не найдёт роут без экспорта Route
export default function HomePage() { ... }
```

---

## Параметры маршрута

```tsx
// src/routes/track/$trackId.tsx
export const Route = createFileRoute("/track/$trackId")({
  component: TrainingPage,
});

function TrainingPage() {
  // ✅ через Route.useParams()
  const { trackId } = Route.useParams();

  // ❌ useParams из react-router-dom не работает
}
```

---

## Корневой layout (\_\_root.tsx)

В TanStack Start `__root.tsx` рендерит весь документ целиком (`<html>`, `<body>`).
Обязательно включай `<HeadContent />` и `<Scripts />`.

```tsx
// src/routes/__root.tsx
import {
  Outlet,
  createRootRoute,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { ConvexAuthProvider } from "@convex-dev/auth/react";
import { ConvexReactClient } from "convex/react";
import type { ReactNode } from "react";

const convex = new ConvexReactClient(import.meta.env.VITE_CONVEX_URL);

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Fingerdrum App" },
    ],
  }),
  component: RootComponent,
});

function RootComponent() {
  return (
    <RootDocument>
      <ConvexAuthProvider client={convex}>
        <Header />
        <Outlet />
      </ConvexAuthProvider>
    </RootDocument>
  );
}

function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html>
      <head>
        <HeadContent /> {/* мета теги, title, CSS */}
      </head>
      <body>
        {children}
        <Scripts /> {/* ОБЯЗАТЕЛЬНО — клиентский JS */}
      </body>
    </html>
  );
}
```

> **Важно**: `<Scripts />` — обязательный компонент, без него клиентский JavaScript не загрузится.

---

## Защита маршрутов

```tsx
// Вариант 1 — проверка в компоненте (проще)
import { useConvexAuth } from "convex/react";
import { Navigate } from "@tanstack/react-router";

function TrainingPage() {
  const { isAuthenticated, isLoading } = useConvexAuth();
  if (isLoading) return <div className="text-white p-8">Загрузка...</div>;
  if (!isAuthenticated) return <Navigate to="/sign-in" />;
  return <TrainingContent />;
}

// Вариант 2 — beforeLoad (выполняется до рендера)
export const Route = createFileRoute("/track/$trackId")({
  beforeLoad: async ({ context }) => {
    if (!context.auth?.isAuthenticated) {
      throw redirect({ to: "/sign-in" });
    }
  },
  component: TrainingPage,
});
```

---

## Навигация

```tsx
import { Link, useNavigate } from "@tanstack/react-router"

// Декларативная
<Link to="/track/$trackId" params={{ trackId: track._id }}>
  Начать тренировку
</Link>

// С query params
<Link to="/" search={{ difficulty: "beginner" }}>Beginner</Link>

// Программная
const navigate = useNavigate()
navigate({ to: "/track/$trackId", params: { trackId } })
navigate({ to: "/", search: { difficulty: "beginner" } })
```

---

## Client-only код (SSR безопасность)

Web Audio API, Web MIDI API — недоступны на сервере.

```tsx
// ✅ инициализация в useEffect — выполняется только на клиенте
useEffect(() => {
  if (!navigator.requestMIDIAccess) return
  navigator.requestMIDIAccess({ sysex: false }).then(...)
}, [])

// ✅ динамический импорт для тяжёлых browser-only модулей
const { Midi } = await import("@tonejs/midi")

// ❌ на верхнем уровне модуля — упадёт при SSR
const ctx = new AudioContext()
```

---

## Переменные окружения

```ts
// ✅ Vite — VITE_ префикс доступен на клиенте
import.meta.env.VITE_CONVEX_URL;

// ❌ только на сервере
process.env.CONVEX_URL;
```

---

## Структура routes/ — два способа именования

TanStack Router поддерживает оба стиля, они эквивалентны:

```
# Стиль 1 — через директории (используем в этом проекте)
src/routes/
├── __root.tsx
├── index.tsx                  # /
├── sign-in.tsx                # /sign-in
├── settings.tsx               # /settings
└── track/
    └── $trackId.tsx           # /track/$trackId

# Стиль 2 — через точку в имени файла (альтернатива)
src/routes/
├── __root.tsx
├── index.tsx                  # /
├── sign-in.tsx                # /sign-in
├── settings.tsx               # /settings
└── track.$trackId.tsx         # /track/$trackId (точка = уровень вложенности)
```

Используй стиль 1 (директории) — он нагляднее для вложенных маршрутов.

---

## Частые ошибки

```tsx
// ❌ нет экспорта Route → TanStack не найдёт страницу
// ❌ useParams из react-router-dom → Route.useParams()
// ❌ хардкод пути в Link → используй params объект
<Link to={`/track/${id}`} />  →  <Link to="/track/$trackId" params={{ trackId: id }} />
// ❌ browser API на верхнем уровне → в useEffect
// ❌ забыть <Scripts /> в __root.tsx → приложение не запустится на клиенте
// ❌ забыть <HeadContent /> → CSS и мета теги не загрузятся
```
