/**
 * Shared Tailwind theme.
 *
 * Loaded on every page directly after the Tailwind CDN script so all pages
 * draw from one palette and type scale instead of each picking its own greys
 * and blues.
 *
 * The palette is deliberately restrained: an election system should read as
 * institutional and trustworthy, so colour is used for meaning (election
 * state, role, destructive actions) rather than decoration.
 */
tailwind.config = {
  theme: {
    extend: {
      colors: {
        // Primary — a deep, slightly desaturated indigo. Confident without
        // being loud, and it holds up against white at small sizes.
        brand: {
          50: "#f2f5ff",
          100: "#e6ebff",
          200: "#ccd6fe",
          300: "#a8b8fb",
          400: "#8193f7",
          500: "#6070ef",
          600: "#4750df",
          700: "#3a3cbd",
          800: "#313399",
          900: "#2c2f7a",
        },
        // Neutrals carry a faint blue undertone so they sit with the brand
        // colour rather than looking muddy next to it.
        ink: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e6ebf2",
          300: "#cfd8e3",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI Variable Text",
          "Segoe UI",
          "Inter",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      // Soft, low-contrast shadows. Heavy drop shadows read as dated; these
      // lift a surface just enough to separate it from the page.
      boxShadow: {
        card: "0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06)",
        lift: "0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)",
        pop: "0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.05)",
      },
      borderRadius: {
        xl: "0.75rem",
        "2xl": "1rem",
      },
    },
  },
};
