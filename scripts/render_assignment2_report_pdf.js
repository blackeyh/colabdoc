const path = require('path')
const { chromium } = require('/Users/mohamed.farrag/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')

async function main() {
  const repoRoot = path.resolve(__dirname, '..')
  const input = path.join(repoRoot, 'ASSIGNMENT2_REPORT_PRINT.html')
  const output = path.join(repoRoot, 'ASSIGNMENT2_REPORT.pdf')
  const executablePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

  const browser = await chromium.launch({ headless: true, executablePath })
  const page = await browser.newPage()
  await page.goto(`file://${input}`, { waitUntil: 'load' })
  await page.pdf({
    path: output,
    format: 'A4',
    printBackground: true,
    preferCSSPageSize: true,
    margin: {
      top: '0',
      right: '0',
      bottom: '0',
      left: '0',
    },
  })
  await browser.close()
  console.log(output)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
