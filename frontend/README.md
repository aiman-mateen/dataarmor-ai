# DataArmor AI — Frontend

Healthcare PHI detection & anonymization platform · Final Year Project · Software Engineering Department, MUET

## Run locally

```bash
npm install
npm run dev
```

Then open the printed local URL (usually http://localhost:5173).

## Build for submission / deployment

```bash
npm run build
npm run preview
```

## Project structure

```
src/
├── components/
│   ├── layout/       Sidebar, Header, Footer — shared app shell
│   └── ui/            Button, Card, Badge, ProgressBar, PageHeader — design system primitives
├── pages/              One file per sidebar view
├── data/
│   └── placeholderData.js   All placeholder content + the fixed PHI class colour mapping
├── App.jsx             Page composition & simple state-based routing
└── main.jsx             React entry point
```

## Colour system

- Primary — Deep Blue (`blue-800`): navigation, primary buttons, headers
- Secondary — Teal (`teal-600`): progress/confidence bars, success states, active-selection highlights, hover accents
- PHI class mapping (fixed everywhere — app, diagrams, slides, report):
  Direct Identifier = red · Quasi-Identifier = orange · Sensitive Attribute = yellow · Non-PHI = grey

No backend is wired up yet — every page uses placeholder data from `src/data/placeholderData.js`, ready to be swapped for real API calls in the next phase.
