# Visual Agent Frontend

The **Visual Agent Frontend** is a React + Vite web interface that allows users to interact with the **Visual Agent AI system**.  
It lets users submit prompts to the backend, which triggers the AI pipeline (YOLO → BLIP → LLM reasoning → results).

This interface provides a simple, modern UI for testing and visualizing the AI workflow.

---

## Tech Stack

- **Framework:** React + Vite  
- **Styling:** CSS Modules + Global CSS  
- **Language:** JavaScript (ES6+)  
- **Backend Integration:** FastAPI (via REST API calls)  
- **Build Tool:** Vite  
- **Design Principle:** Minimalist, responsive, and modular  

---

## Folder Structure

```

frontend/
│
├── public/                # Static assets (favicon, logo, etc.)
│
├── src/
│   ├── assets/            # Image and static resources
│   ├── components/        # Reusable React components
│   │   ├── BrandHeader.jsx   # Logo + project title header
│   │   ├── LeftColumn.jsx    # Intro text, CTA, and branding area
│   │   └── PromptForm.jsx    # Main form for prompt submission
│   │
│   ├── App.jsx            # Main app layout (Left + Right sections)
│   ├── App.module.css     # Scoped CSS module for page layout
│   ├── App.css            # Global styles reset (root layout)
│   ├── index.css          # Global style variables and font settings
│   ├── api.js             # Helper functions to interact with backend API
│   └── main.jsx           # React app entry point
│
├── .env                   # Environment variables (API URL)
├── vite.config.js         # Vite configuration
├── package.json           # Project dependencies and scripts
└── README.md              # This file

```

---

## 🚀 Getting Started

### 1. Clone the Repository

If this project is part of a larger repo, navigate to the frontend folder:

```bash
git clone <repo-url>
cd frontend
````

---

### 2. Install Dependencies

Make sure you have **Node.js ≥ 18** installed.

```bash
npm install
```

---

### 3. Set Up Environment Variables

Create a `.env` file in the `frontend` folder (if it doesn’t exist yet):

```bash
VITE_API_URL=http://127.0.0.1:8000
```

> ⚠️ This should match your backend’s local development address.

---

### 4. Run the Development Server

Start the Vite dev server:

```bash
npm run dev
```

Then open your browser to:

 **[http://localhost:5173](http://localhost:5173)**

You should see the **Visual Agent** web app running locally.

---

## Connecting to the Backend

This frontend expects a running **FastAPI backend** (see `/backend/README.md` for setup).
Make sure your backend is running at the same time (default: port `8000`).

API calls are defined in `src/api.js`:

* `POST /api/run` → Start the AI pipeline
* `GET /api/status/{run_id}` → Get live pipeline status
* `POST /api/reprompt` → Send additional user input to the backend

---

## Features

* **Responsive two-column layout** (intro text on the left, AI form on the right)
* **Modern UI** with soft color palette and animations
* **Logo + project branding** via `BrandHeader.jsx`
* **Interactive prompt form** (accepts text prompts)
* **Status log output** for tracking pipeline progress

---

## Styling and Theming

The app uses a **modular CSS structure**:

| File             | Purpose                            |
| ---------------- | ---------------------------------- |
| `App.module.css` | Layout, colors, and responsiveness |
| `App.css`        | Root container and global resets   |
| `index.css`      | Global typography and defaults     |

### Color Palette

| Role      | Color     | Description                        |
| --------- | --------- | ---------------------------------- |
| Dominant  | `#EFEFEF` | Light, modern background           |
| Secondary | `#0e3558` | Deep blue for headings             |
| Accent    | `#faaa47` | Orange accent for CTAs and buttons |
| Neutral   | `#F8F8F8` | Light surfaces and sections        |

---

## Available Scripts

| Command           | Description                         |
| ----------------- | ----------------------------------- |
| `npm run dev`     | Start local dev server (hot reload) |
| `npm run build`   | Create production build             |
| `npm run preview` | Preview production build locally    |
| `npm run lint`    | Run ESLint checks                   |

---

## Component Overview

| Component           | Description                                                         |
| ------------------- | ------------------------------------------------------------------- |
| **BrandHeader.jsx** | Displays the project logo and title (top-left).                     |
| **LeftColumn.jsx**  | Shows the welcome message, description, and call to action.         |
| **PromptForm.jsx**  | Handles user input and communicates with the backend. |

---

## Environment Variable Reference

| Variable       | Description                          | Example                 |
| -------------- | ------------------------------------ | ----------------------- |
| `VITE_API_URL` | The URL where the backend is hosted. | `http://127.0.0.1:8000` |

---

## Development Notes

* Keep API endpoints centralized in `src/api.js`.
* For visual changes, update only `App.module.css`.
* The UI dynamically adapts to different screen sizes (desktop, tablet, mobile).
* The project uses **ESLint** for code quality and formatting.

---

## Troubleshooting

| Issue                                | Fix                                                              |
| ------------------------------------ | ---------------------------------------------------------------- |
| Frontend cannot reach backend        | Ensure backend is running on port `8000` and `.env` file matches |
| Button colors or layout not updating | Stop server and restart with `npm run dev` (Vite caches styles)  |

---

## Team Notes

* The frontend is designed to integrate seamlessly with the backend (FastAPI).
* All UI changes should go through `App.module.css` for consistent styling.
* Avoid pushing `.env` files to version control.
* When adding new components, place them under `src/components/` and use CSS modules for scoped styles.

---

## Next Steps

* [ ] Add component for reprompting. 
* [ ] Add loading spinners and visual feedback for pipeline progress.
* [ ] Add error states for failed requests.
* [ ] Improve accessibility (ARIA labels, keyboard navigation).

---

## Summary

The **Visual Agent Frontend** provides the interactive web interface for testing and visualizing AI capabilities from the backend.
It’s built for simplicity, modularity, and quick iteration — making it easy for every group member to develop, debug, and extend.

---



