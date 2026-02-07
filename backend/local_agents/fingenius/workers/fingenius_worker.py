import asyncio
import multiprocessing
import signal
import sys

from local_agents.fingenius.main import fingenius_main


def worker_process(task_queue):
    """
    一个后台工作进程，从队列中获取任务并执行
    """

    # 注册信号处理器以实现优雅退出
    def cleanup_handler(signum, frame):
        print(f"工作进程收到信号 {signum}，正在退出...")
        # 这里的清理逻辑可以根据需要添加
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)

    print("后台工作进程已启动，等待任务...")
    while True:
        try:
            # 从队列中获取任务，等待1秒以允许正常退出
            stock_code = task_queue.get(timeout=1)
            print(f"工作进程开始处理股票代码: {stock_code}")

            # 使用 asyncio.run 在后台进程中执行异步任务
            asyncio.run(fingenius_main(stock_code), debug=True)

            print(f"股票代码 {stock_code} 的任务完成")
        except multiprocessing.queues.Empty:
            # 如果队列为空，继续等待
            continue
        except Exception as e:
            print(f"工作进程执行任务时出错: {e}")


# 这是工作进程的入口
if __name__ == "__main__":
    # 在 worker 进程中，设置 spawn 启动方法
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # 已经在主进程中设置过，忽略

    # 创建一个队列来传递任务
    task_queue = multiprocessing.Queue()

    # 启动工作进程
    worker = multiprocessing.Process(target=worker_process, args=(task_queue,))
    worker.daemon = True  # 确保主进程退出时子进程也退出
    worker.start()

    # 在主进程中，你可以使用 task_queue.put() 来添加任务
    # 例如：task_queue.put('AAPL')
    # ... 在这里，你可以启动你的 Flask 应用