interface ErrorBannerProps {
  message: string
  onDismiss: () => void
}

function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      <button
        type="button"
        className="error-dismiss"
        onClick={onDismiss}
        aria-label="Dismiss error"
      >
        ✕
      </button>
    </div>
  )
}

export default ErrorBanner
