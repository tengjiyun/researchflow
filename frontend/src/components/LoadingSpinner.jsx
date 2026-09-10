// 纯展示组件用于在数据加载时显示提示信息,不接收任何 props，也不管理状态

function LoadingSpinner() {
    return (
      <div className="loading-spinner">
        <p>Loading...</p>
      </div>
    )
  }
  
  export default LoadingSpinner