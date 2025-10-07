import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright


def detect_latest_html_file(search_directory: Path) -> Optional[Path]:
	"""Find the most recently modified .html file in the directory.

	Args:
		search_directory: Directory to scan for HTML files.

	Returns:
		Path to the newest HTML file, or None if not found.
	"""
	html_files = sorted(search_directory.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
	return html_files[0] if html_files else None


def to_file_uri(file_path: Path) -> str:
	"""Convert a local path to a file:// URI that Chromium can load."""
	return file_path.resolve().as_uri()


async def inject_print_color_css(page) -> None:
	"""Force exact print color rendering to keep backgrounds and colors."""
	css = """
	  html, body, * {
	    -webkit-print-color-adjust: exact !important;
	    print-color-adjust: exact !important;
	    color-adjust: exact !important;
	  }

	  /* 分页优化，尽可能保持图片与标题/说明不被拆分 */
	  figure,
	  .figure,
	  .image-block,
	  .img-block,
	  .chart,
	  .table,
	  .table-wrapper,
	  .keep-together,
	  .__pdf_keep_together {
	    break-inside: avoid-page !important;
	    page-break-inside: avoid !important;
	  }

	  img,
	  svg,
	  figcaption,
	  .caption,
	  .image-title,
	  .image-name {
	    break-inside: avoid-page !important;
	    page-break-inside: avoid !important;
	  }

	  table, thead, tbody, tfoot, tr, td, th {
	    break-inside: avoid !important;
	    page-break-inside: avoid !important;
	  }

	  h1, h2, h3, h4, h5, h6 {
	    break-after: avoid-page !important;
	    page-break-after: avoid !important;
	  }

	  p, li, blockquote {
	    orphans: 3;
	    widows: 3;
	  }
	"""
	await page.add_style_tag(content=css)


async def inject_layout_safety_css(page) -> None:
	"""注入布局安全样式，避免超宽元素溢出与被分页裁剪。

	- 使图片/图表自适应宽度
	- 表格固定布局并允许单元格换行
	- 代码块/长文本自动换行
	- 提供.page-break类用于强制分页
	"""
	css = """
	  html, body {
	    margin: 0;
	    padding: 0;
	    overflow: visible !important;
	  }

	  img, svg, canvas, video {
	    max-width: 100% !important;
	    height: auto !important;
	    page-break-inside: avoid !important;
	    break-inside: avoid-page !important;
	  }

	  .section, .block, .card, .panel, .chart, .figure, figure, .table-wrapper, .keep-together, .__pdf_keep_together {
	    page-break-inside: avoid !important;
	    break-inside: avoid-page !important;
	  }

	  table {
	    width: 100% !important;
	    table-layout: fixed !important;
	    border-collapse: collapse;
	  }
	  th, td {
	    word-break: break-word;
	    overflow-wrap: anywhere;
	  }

	  pre, code, .code, .log, .nowrap {
	    white-space: pre-wrap !important;
	    word-break: break-word !important;
	  }

	  .page-break {
	    page-break-before: always !important;
	    break-before: page !important;
	  }
	"""
	await page.add_style_tag(content=css)


async def ensure_lazy_content_rendered(page) -> None:
	"""Trigger lazy-loaded content by scrolling the page before printing."""
	await page.evaluate(
		"""
		async () => {
		  const delay = (ms) => new Promise(r => setTimeout(r, ms));
		  const totalHeight = document.body.scrollHeight || document.documentElement.scrollHeight;
		  const viewport = window.innerHeight || 800;
		  for (let y = 0; y < totalHeight; y += Math.max(100, viewport / 2)) {
		    window.scrollTo(0, y);
		    await delay(80);
		  }
		  window.scrollTo(0, 0);
		}
		"""
	)


async def group_images_with_captions(page) -> None:
	"""Heuristically group images with their captions to avoid page breaks between them.

	- If an <img> is inside <figure>, mark the figure as keep-together
	- If a caption-like sibling follows the image, wrap both into a keep-together container
	"""
	await page.evaluate(
		"""
		(() => {
		  const isCaptionLike = (el) => {
		    if (!el) return false;
		    const tag = (el.tagName || '').toLowerCase();
		    if (tag === 'figcaption' || tag === 'caption') return true;
		    const cls = (el.className || '').toString().toLowerCase();
		    if (/(caption|titl|name)/.test(cls)) return true;
		    const text = (el.textContent || '').trim();
		    if (text && text.length < 80 && /(图|figure|fig\.|表|table)/i.test(text)) return true;
		    return false;
		  };

		  const ensureKeepTogether = (el) => {
		    if (!el) return;
		    el.classList.add('__pdf_keep_together');
		    el.style.breakInside = 'avoid-page';
		    el.style.pageBreakInside = 'avoid';
		    if (!getComputedStyle(el).display || getComputedStyle(el).display === 'inline') {
		      el.style.display = 'block';
		    }
		    if (!el.style.width) {
		      el.style.width = '100%';
		    }
		  };

		  const imgs = Array.from(document.images || []);
		  for (const img of imgs) {
		    const figure = img.closest && img.closest('figure');
		    if (figure) {
		      ensureKeepTogether(figure);
		      continue;
		    }
		    const next = img.nextElementSibling;
		    if (isCaptionLike(next)) {
		      const wrapper = document.createElement('div');
		      wrapper.className = '__pdf_keep_together';
		      wrapper.style.breakInside = 'avoid-page';
		      wrapper.style.pageBreakInside = 'avoid';
		      wrapper.style.display = 'block';
		      wrapper.style.width = '100%';
		      const parent = img.parentNode;
		      if (parent) {
		        parent.insertBefore(wrapper, img);
		        wrapper.appendChild(img);
		        if (next && next.parentNode === parent) {
		          wrapper.appendChild(next);
		        }
		      }
		      continue;
		    }
		    const parent = img.parentElement;
		    if (parent && parent.childElementCount === 1) {
		      ensureKeepTogether(parent);
		    }
		  }
		})();
		"""
	)


async def convert_html_to_pdf(
	input_html_path: Path,
	output_pdf_path: Path,
	media: str = "screen",
	wait_state: str = "networkidle",
	page_format: Optional[str] = None,
	landscape: bool = False,
):
	"""Render a local HTML file to PDF using Chromium via Playwright.

	Key options to preserve fidelity:
	- emulate screen media to keep on-screen styles
	- print_background=True to keep background colors/images
	- prefer_css_page_size=True so @page size in CSS is respected
	"""
	file_url = to_file_uri(input_html_path)
	async with async_playwright() as p:
		# 检查是否有便携版浏览器
		portable_chrome_path = None
		possible_paths = [
			Path("./chrome-portable/chrome.exe"),  # 当前目录
			Path("./chromium-portable/chrome.exe"),
			Path("./browser/chrome.exe"),
			Path("./chrome/chrome.exe"),
			Path("C:/chrome-portable/chrome.exe"),  # 固定位置
			Path("C:/chromium-portable/chrome.exe"),
		]
		
		for path in possible_paths:
			if path.exists():
				portable_chrome_path = str(path.absolute())
				# 使用统一日志格式
				try:
					from logger_utils import log_ai_message
					log_ai_message("PDF", f"检测到便携版Chrome: {portable_chrome_path}")
				except:
					print(f"✅ 检测到便携版Chrome: {portable_chrome_path}")
				break
		
		if not portable_chrome_path:
			try:
				from logger_utils import log_ai_message
				log_ai_message("PDF", "未检测到便携版Chrome，将使用Playwright安装的浏览器")
			except:
				print("⚠️  未检测到便携版Chrome，将使用Playwright安装的浏览器")
		
		# 启动浏览器
		if portable_chrome_path:
			# 使用便携版浏览器
			try:
				from logger_utils import log_ai_message
				log_ai_message("PDF", "使用便携版Chrome启动浏览器")
			except:
				pass
			browser = await p.chromium.launch(executable_path=portable_chrome_path)
		else:
			# 使用Playwright安装的浏览器
			try:
				from logger_utils import log_ai_message
				log_ai_message("PDF", "使用Playwright Chromium启动浏览器")
			except:
				pass
			try:
				browser = await p.chromium.launch()
			except Exception as e:
				if "Executable doesn't exist" in str(e):
					try:
						from logger_utils import log_ai_message
						log_ai_message("ERROR", "未找到Chromium浏览器，请安装或提供便携版Chrome")
					except:
						print("错误：未找到Chromium浏览器")
						print("请选择以下方法之一：")
						print("1. 运行: py -m playwright install chromium")
						print("2. 下载便携版Chrome并解压到 ./chrome-portable/ 目录")
					raise
				else:
					raise
		
		context = await browser.new_context()
		page = await context.new_page()
		# Screen media helps preserve backgrounds and layout typical of on-screen report HTML
		await page.emulate_media(media=media)
		await page.goto(file_url, wait_until=wait_state)
		await inject_print_color_css(page)
		await inject_layout_safety_css(page)
		await group_images_with_captions(page)
		await ensure_lazy_content_rendered(page)
		# Wait a bit more for any post-scroll lazy resources
		await page.wait_for_load_state("networkidle")
		pdf_options = {
			"print_background": True,
			"prefer_css_page_size": True,
			"landscape": landscape,
			"margin": {
				"top": "12mm",
				"right": "12mm",
				"bottom": "12mm",
				"left": "12mm",
			},
			# 轻微缩放，减少被裁剪概率；若模板自带@page可忽略
			"scale": 0.95,
		}
		if page_format:
			pdf_options["format"] = page_format
		else:
			# 默认A4，更符合医疗报告打印习惯
			pdf_options["format"] = "A4"
		# Ensure parent directory exists for output
		output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
		await page.pdf(path=str(output_pdf_path), **pdf_options)
		await context.close()
		await browser.close()


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="高保真 HTML 转 PDF (Chromium/Playwright)")
	parser.add_argument("input_html", nargs="?", help="输入 HTML 文件路径，不填则自动选择目录下最新的 .html")
	parser.add_argument("output_pdf", nargs="?", help="输出 PDF 文件路径，默认与输入同名 .pdf")
	parser.add_argument("--format", dest="page_format", default=None, help="纸张格式，如 A4、Letter；若 HTML 有 @page，则无需设置")
	parser.add_argument("--landscape", action="store_true", help="横向打印")
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	cwd = Path.cwd()
	input_path: Optional[Path]
	if args.input_html:
		input_path = Path(args.input_html)
	else:
		input_path = detect_latest_html_file(cwd)
		if not input_path:
			raise SystemExit("未找到 .html 文件，请指定输入路径")
	if not input_path.exists():
		raise SystemExit(f"输入文件不存在: {input_path}")
	if args.output_pdf:
		output_path = Path(args.output_pdf)
	else:
		output_path = input_path.with_suffix(".pdf")
	print(f"转换: {input_path} -> {output_path}")
	asyncio.run(
		convert_html_to_pdf(
			input_html_path=input_path,
			output_pdf_path=output_path,
			media="screen",
			wait_state="networkidle",
			page_format=args.page_format,
			landscape=args.landscape,
		)
	)
	print("完成 ✅")


if __name__ == "__main__":
	main()


