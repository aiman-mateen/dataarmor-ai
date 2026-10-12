export function downloadTextFile(filename, content, mimeType = "text/plain") {
  const needsBom = mimeType === "text/csv" || mimeType === "text/plain";
  const finalContent = needsBom ? "\uFEFF" + content : content;
  const blob = new Blob([finalContent], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}