const urlPattern = /^https?:\/\/([\w-]+\.)+[\w-]+(\/\S*)?$/i

export function isUrl(input) {
  return urlPattern.test((input || "").trim())
}
