# 🧠 PROJECT_RULES.md — Forever Yours Compression Tool

This project follows strict development and structure rules to ensure it's clean, modular, ADHD-friendly, and easy to maintain.

## ✅ Rules to Follow

1. **Modular Code Only**
   - Break all logic into small, single-purpose Python modules.
   - Each file should stay under **150 lines**. Split into separate files/modules if it grows beyond that.

2. **Function Scope**
   - Each function should only do **one clear thing**.
   - If it starts doing multiple jobs, refactor it.

3. **Directory Structure**
   - Keep GUI code in `gui/` only.
   - Keep business logic and operations in `core/`.
   - Store logs in `logs/`.
   - Keep the root folder clean and only for entry point scripts and Markdown references.

4. **Nesting and Complexity**
   - No more than 2 levels of nested logic in any function.
   - If conditionals or loops go deeper, extract them into their own functions.

5. **Clean UI Code**
   - GUI files should handle layout and event connections only.
   - They should **call functions** from the `core/` folder — never embed logic directly.

6. **Naming and Simplicity**
   - Use clear, consistent naming.
   - Avoid premature optimization, overengineering, or trying to be “clever.”
   - Simpler is better.

7. **Refactor Aggressively**
   - If a block grows too complex, split it and document the change.
   - Leave clear TODOs or `# REFACTOR:` comments if needed.

8. **Log Cleanly**
   - All logging should write to `logs/compress.log`.
   - No print() calls outside of test/debug files.

---

By following these rules, we can keep this project fast to navigate, safe to edit, and easy to reason about — even when context-switching or picking it up weeks later.
