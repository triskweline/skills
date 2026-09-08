# Formatting tricks in terminal-based sessions

In most terminal-based sessions, you are limited to a simple Markdown renderer on a character matrix. Some tricks still make your output more visually pleasing, easier to scan, and more engaging and varied:

- Use everything Markdown offers to structure long outputs. Use headlines, tables and code blocks where they make your output clearer and prettier.
- Apply all available character formatting like inline code, bold, italic and strike-through to make words stand out.
- Use emojis where you would use icons in a richer output format. Apply a measured amount, to emphasize a point, to distinguish sections, or as an additional information channel when you're running out of formatting options. Don't flood the human with emojis, don't make it look like a teenager's chat.
- Separate turns and narration beats with ASCII-art lines (e.g. 120 characters of `═` or `─`).
- Where helpful, use code blocks with ASCII art drawings. Some useful characters are below. These can help you visualize bars, boxes, charts or basic shapes. Make sure any drawings are truly helpful and worth their generation time and screen space. E.g. don't visualize a trivial `if...then` statement using two boxes with an arrow.
- Never write a script to produce a drawing. If a shape needs code to align, pick a simpler shape.
- Keep emojis out of aligned tables and drawings. They are two cells wide and break column alignment. Use them in prose and headings, where width doesn't matter.
- Use the full width of the current terminal. If you cannot determine terminal size, assume 120 columns.


## Useful characters

The model knows these already. This is a reminder of which families are safe in nearly every terminal font:

```
Lines and corners   ─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼      heavy: ━ ┃     double: ═ ║ ╔ ╗ ╚ ╝ ╠ ╣
Rounded corners     ╭ ╮ ╰ ╯
Bars and shading    █ ▓ ▒ ░      partial blocks: ▏▎▍▌▋▊▉      vertical: ▁▂▃▄▅▆▇
Marks               ● ○ ◆ ◇ ■ □ ▲ ▼ ► ◄ ✓ ✗ → ←
```

Avoid the "Symbols for Legacy Computing" block (U+1FB00 and up). Most terminal fonts lack it, and a chart drawn with it renders as empty boxes.
