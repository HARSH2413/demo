# DocIntel Frontend Audit Report

## 1. Executive Summary
The DocIntel frontend is built with Next.js 16 (App Router), React, and Tailwind CSS. The application successfully implements the new Box-first architecture, allowing users to create isolated workspaces (Boxes), upload documents, and perform RAG-based AI chat. 

The core functionalities (auth, box creation, document upload, and chat) are highly operational following recent bug fixes. However, the application currently lacks a unified global layout. The Dashboard (`/boxes`) and the Box Interface (`/boxes/[box_id]`) are isolated experiences. Furthermore, the Box Interface is not mobile-responsive, and legacy "Knowledge Base" terminology is still used interchangeably with Box documents.

## 2. Complete Route Inventory
| Route | Component/File | Type | Status | Purpose & Issues |
|---|---|---|---|---|
| `/` | `app/page.tsx` | Server | ✅ Complete | Landing page. Visually rich, operational CTAs. |
| `/login` | `app/login/page.tsx` | Client | ✅ Complete | User login. Excellent UI. |
| `/signup` | `app/signup/page.tsx` | Client | ✅ Complete | User signup. Features instant password validation. |
| `/onboarding` | `app/onboarding/page.tsx` | Server | ✅ Complete | Forces initial Box creation. |
| `/boxes` | `app/boxes/page.tsx` & `BoxesClient.tsx` | Server/Client | ⚠️ Partial | Lists all Boxes. Missing global navigation/sign out. |
| `/boxes/[box_id]` | `app/boxes/[box_id]/page.tsx` & `ChatDashboard.tsx` | Server/Client | ⚠️ Partial | Core Box interface. Functional but breaks on mobile. |
| `/workspace/chat` | `app/workspace/chat/page.tsx` | Server | ❌ Deprecated | Legacy route. Hard redirects to `/boxes`. |
| `/auth/*` | `actions.ts`, `callback`, `logout` | Server | ✅ Complete | Supabase auth routing. |

## 3. Navigation and Layout Audit
- **No Global App Shell:** There is no standard layout wrapper for authenticated users. The `/boxes` page has no navigation bar, meaning users cannot access settings, profile, or even "Sign Out" from the main dashboard.
- **Box-Specific Sidebar:** The sidebar inside `ChatDashboard.tsx` acts as the sole navigation for the app, but it is trapped inside individual Boxes.
- **Sign Out Placement:** The "Sign Out" button is buried at the bottom of the Box sidebar. You cannot sign out if you are on the `/boxes` list page without entering a Box first.
- **Mobile Navigation:** There is zero mobile navigation. The sidebar is fixed to `w-72`, and the split-pane document viewer takes `w-1/2`, which will completely overlap or break on mobile devices.

## 4. Screen-by-Screen UI Audit
### Landing Page
- **UI:** Stunning dark-mode aesthetic with animations and mockups.
- **Issues:** None. Fully responsive and accessible.

### Login / Signup
- **UI:** Minimalist, sleek authentication forms.
- **Issues:** None. Password toggles and match validation work perfectly.

### Boxes Dashboard (`/boxes`)
- **UI:** Clean grid view with empty states and hover-to-delete actions.
- **Issues:** The user is trapped here. No header, no avatar, no logout button.

### Box Interface / Chat (`/boxes/[box_id]`)
- **UI:** Premium split-pane RAG interface. Left side is Chat, right side is Document Citation Viewer.
- **Issues:** 
  - **Responsiveness:** Fixed widths make it unusable on mobile.
  - **State Overload:** The component manages massive amounts of state (chat, files, syncing).
  - **Terminology:** The document list is labeled "Knowledge Base" in the sidebar, which conflicts with the product direction to treat "Knowledge Base" as a separate, future feature.

## 5. Box Workflow Audit
The Box-first workflow is completely functional from end-to-end:
1. **Access:** Users authenticate and select a Box. The recent "Box Not Found" bug (caused by Next.js 15+ `Promise` route params) has been **confirmed fixed**.
2. **Ingestion:** Users upload PDFs via the `KnowledgeBaseView.tsx` component. The UI correctly polls for processing status.
3. **Querying:** Users type in the chat. The backend returns AI responses with citations.
4. **Verification:** Clicking a citation opens `activeDoc` in a right-hand pane, displaying the exact source text or PDF iframe.

## 6. Knowledge Base Audit
Currently, the application does not have a distinct global "Knowledge Base". Instead, the term "Knowledge Base" is used inside `ChatDashboard.tsx` to describe the Box's file index.
- **Sidebar Button:** "Library -> Knowledge Base"
- **Component:** `<KnowledgeBaseView />`

To align with the goal of marking "Knowledge Base" as "Coming Soon", we must decouple the Box's document index from the "Knowledge Base" terminology.

## 7. Technical Issues
- **Component Bloat:** `ChatDashboard.tsx` is nearly 600 lines long. It should be refactored to use custom hooks (e.g., `useChat`, `useDocuments`).
- **Responsiveness:** Missing mobile breakpoints and hamburger menus in the dashboard.
- **TypeScript Warnings:** A few `any` types remain in `src/lib/api.ts` and `BoxesClient.tsx`.
- **Legacy Files:** `/workspace` directory should be safely deleted since it only contains a redirect.

---

## 8. Frontend Completion Roadmap

### Priority 1: Main Application Layout & Navigation
**Task 1.1: Global Authenticated Shell**
- **Files:** `src/app/(authenticated)/layout.tsx`, `src/components/layout/Topbar.tsx`
- **What:** Create a persistent Topbar containing a breadcrumb navigation, User Profile avatar, and Sign Out button. Apply this layout to `/boxes`.
- **Why:** Users currently have no way to sign out or view their profile from the main dashboard.

### Priority 2: Terminology and Knowledge Base
**Task 2.1: Rename Box Documents & Stub Knowledge Base**
- **Files:** `src/app/workspace/chat/ChatDashboard.tsx`, `src/app/knowledge-base/page.tsx`
- **What:** Rename "Knowledge Base" in the Box sidebar to "Documents". Create a new global route `/knowledge-base` that displays a premium "Coming Soon" placeholder screen.
- **Why:** Satisfies the product requirement to reserve the Knowledge Base feature for future development while keeping the Box workflow clear.

### Priority 3: Responsive Design
**Task 3.1: Mobile Dashboard Refactor**
- **Files:** `src/app/workspace/chat/ChatDashboard.tsx`
- **What:** Make the `w-72` sidebar collapsible behind a hamburger menu on mobile (`md:hidden`). Change the `w-1/2` citation side-panel to an overlay or stacked layout on mobile screens.
- **Why:** The core product is currently unusable on phones.

### Priority 4: Code Quality & Technical Debt
**Task 4.1: Extract Dashboard State into Hooks**
- **Files:** `src/app/workspace/chat/ChatDashboard.tsx`, `src/hooks/useChat.ts`, `src/hooks/useDocuments.ts`
- **What:** Move `fetchDocuments`, `uploadFiles`, and `handleSendMessage` logic into dedicated React hooks.
- **Why:** The dashboard component is too large and hard to maintain.

---

## 9. Recommended First Implementation Task
**Start with Task 1.1: Global Authenticated Shell.**
Before redesigning complex interfaces, the app needs a fundamental navigational anchor. Adding a Topbar to `/boxes` will immediately fix the inability to log out from the dashboard and set the foundation for user settings.
