// 展示错误信息,接收一个 message 属性
// 如果没有 message，则不渲染任何内容（返回 null）

function ErrorMessage({ message }) {
    // 没有错误信息时直接返回 null，避免渲染空元素
    if (!message) return null
  
    return (
      <div className="error-message">
        <p>{message}</p>
      </div>
    )
  }
  
  export default ErrorMessage