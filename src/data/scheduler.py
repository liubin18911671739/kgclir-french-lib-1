"""
数据更新调度器模块

提供自动化数据获取、更新和监控功能，包括：
- 定时任务调度和执行
- 数据更新策略和版本管理
- 监控和告警机制
- 任务队列和并发控制
"""

import json
import logging
import asyncio
import schedule
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import sqlite3
import hashlib
from enum import Enum

# 本地导入
from ..utils.io import load_yaml, save_yaml
from ..utils.logger import setup_logger
from .connectors import DataRecord, AcademicDatabaseConnector, OpenDataConnector
from .quality_control import DataQualityController

# 设置日志
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class ScheduledTask:
    """调度任务"""
    id: str
    name: str
    description: str
    task_type: str  # 'data_acquisition', 'quality_check', 'update', etc.
    schedule: str  # cron-like expression or interval
    connector_config: Dict[str, Any]
    parameters: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    enabled: bool = True
    max_retries: int = 3
    retry_delay: int = 300  # seconds
    timeout: int = 3600  # seconds
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class TaskExecution:
    """任务执行记录"""
    id: str
    task_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.RUNNING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    records_processed: int = 0
    records_added: int = 0
    records_updated: int = 0
    records_failed: int = 0
    execution_time: float = 0.0

class BaseScheduler(ABC):
    """调度器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=config.get('max_workers', 4))
        self.logger = setup_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def add_task(self, task: ScheduledTask) -> bool:
        """添加任务"""
        pass

    @abstractmethod
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        pass

    @abstractmethod
    def start(self) -> None:
        """启动调度器"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止调度器"""
        pass

    @abstractmethod
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        pass

class TaskScheduler(BaseScheduler):
    """任务调度器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_path = config.get('database_path', 'data/scheduler.db')
        self.max_concurrent_tasks = config.get('max_concurrent_tasks', 3)
        self.running_tasks: Dict[str, TaskExecution] = {}
        self.task_history: List[TaskExecution] = []
        self.task_callbacks: Dict[str, List[Callable]] = {}
        self._init_database()
        self._load_tasks()

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                task_type TEXT NOT NULL,
                schedule TEXT NOT NULL,
                connector_config TEXT,
                parameters TEXT,
                priority INTEGER DEFAULT 2,
                enabled BOOLEAN DEFAULT 1,
                max_retries INTEGER DEFAULT 3,
                retry_delay INTEGER DEFAULT 300,
                timeout INTEGER DEFAULT 3600,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建执行记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_executions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                records_processed INTEGER DEFAULT 0,
                records_added INTEGER DEFAULT 0,
                records_updated INTEGER DEFAULT 0,
                records_failed INTEGER DEFAULT 0,
                execution_time REAL DEFAULT 0.0,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_next_run ON tasks (next_run)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_execution_task_id ON task_executions (task_id)')

        conn.commit()
        conn.close()

    def _load_tasks(self):
        """从数据库加载任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM tasks WHERE enabled = 1')
        rows = cursor.fetchall()

        for row in rows:
            task = self._row_to_task(row)
            if task:
                self.tasks[task.id] = task
                # 设置调度
                self._schedule_task(task)

        conn.close()
        self.logger.info(f"加载了 {len(self.tasks)} 个任务")

    def add_task(self, task: ScheduledTask) -> bool:
        """添加任务"""
        try:
            # 验证任务配置
            if not self._validate_task(task):
                return False

            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO tasks
                (id, name, description, task_type, schedule, connector_config, parameters,
                 priority, enabled, max_retries, retry_delay, timeout, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.id, task.name, task.description, task.task_type, task.schedule,
                json.dumps(task.connector_config), json.dumps(task.parameters),
                task.priority.value, task.enabled, task.max_retries, task.retry_delay,
                task.timeout, task.status.value, datetime.now()
            ))

            conn.commit()
            conn.close()

            # 添加到内存
            self.tasks[task.id] = task

            # 设置调度
            if task.enabled:
                self._schedule_task(task)

            self.logger.info(f"添加任务: {task.name} ({task.id})")
            return True

        except Exception as e:
            self.logger.error(f"添加任务失败: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        try:
            if task_id in self.tasks:
                # 取消正在运行的任务
                if task_id in self.running_tasks:
                    self._cancel_running_task(task_id)

                # 从数据库删除
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()
                conn.close()

                # 从内存删除
                del self.tasks[task_id]

                self.logger.info(f"移除任务: {task_id}")
                return True
            else:
                self.logger.warning(f"任务不存在: {task_id}")
                return False

        except Exception as e:
            self.logger.error(f"移除任务失败: {e}")
            return False

    def start(self) -> None:
        """启动调度器"""
        if self.running:
            self.logger.warning("调度器已在运行")
            return

        self.running = True
        self.logger.info("调度器启动")

        # 启动主循环
        self._run_scheduler()

    def stop(self) -> None:
        """停止调度器"""
        if not self.running:
            return

        self.running = False
        self.logger.info("正在停止调度器...")

        # 取消所有运行中的任务
        for task_id in list(self.running_tasks.keys()):
            self._cancel_running_task(task_id)

        # 等待所有任务完成
        self.executor.shutdown(wait=True)
        self.logger.info("调度器已停止")

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        if task_id in self.running_tasks:
            return self.running_tasks[task_id].status
        elif task_id in self.tasks:
            return self.tasks[task_id].status
        else:
            return None

    def get_task_history(self, task_id: str = None, limit: int = 50) -> List[TaskExecution]:
        """获取任务执行历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if task_id:
            cursor.execute('''
                SELECT * FROM task_executions
                WHERE task_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            ''', (task_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM task_executions
                ORDER BY started_at DESC
                LIMIT ?
            ''', (limit,))

        rows = cursor.fetchall()
        executions = [self._row_to_execution(row) for row in rows]
        conn.close()

        return executions

    def _validate_task(self, task: ScheduledTask) -> bool:
        """验证任务配置"""
        if not task.id or not task.name:
            self.logger.error("任务ID和名称不能为空")
            return False

        if not task.task_type:
            self.logger.error("任务类型不能为空")
            return False

        if not task.schedule:
            self.logger.error("调度配置不能为空")
            return False

        if not task.connector_config:
            self.logger.error("连接器配置不能为空")
            return False

        return True

    def _schedule_task(self, task: ScheduledTask):
        """设置任务调度"""
        try:
            # 解析调度表达式
            if task.schedule.startswith('every_'):
                # 间隔调度: every_5m, every_1h, every_1d
                interval_parts = task.schedule.split('_')
                if len(interval_parts) == 2:
                    interval_value, interval_unit = interval_parts
                    interval_value = int(interval_value[:-1]) if interval_value[:-1].isdigit() else int(interval_value)
                    interval_unit = interval_value[-1]

                    seconds = self._convert_interval_to_seconds(interval_value, interval_unit)
                    schedule.every(seconds).seconds.do(self._execute_task, task)

            elif task.schedule.startswith('daily_'):
                # 每日调度: daily_09:00
                time_str = task.schedule.split('_', 1)[1]
                hour, minute = map(int, time_str.split(':'))
                schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self._execute_task, task)

            elif task.schedule.startswith('weekly_'):
                # 每周调度: weekly_monday_09:00
                parts = task.schedule.split('_', 2)
                if len(parts) == 3:
                    day = parts[1]
                    time_str = parts[2]
                    hour, minute = map(int, time_str.split(':'))
                    getattr(schedule.every(), day.lower()).at(f"{hour:02d}:{minute:02d}").do(self._execute_task, task)

            else:
                self.logger.error(f"不支持的调度格式: {task.schedule}")

        except Exception as e:
            self.logger.error(f"设置任务调度失败: {e}")

    def _convert_interval_to_seconds(self, value: int, unit: str) -> int:
        """转换时间间隔为秒"""
        unit_map = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        return value * unit_map.get(unit, 60)

    def _run_scheduler(self):
        """运行调度器主循环"""
        while self.running:
            try:
                # 运行待执行的任务
                schedule.run_pending()

                # 检查任务超时
                self._check_timeouts()

                # 清理完成的任务
                self._cleanup_completed_tasks()

                # 等待一段时间
                time.sleep(10)

            except Exception as e:
                self.logger.error(f"调度器运行错误: {e}")
                time.sleep(60)  # 出错时等待更长时间

    def _execute_task(self, task: ScheduledTask):
        """执行任务"""
        if not self.running:
            return

        # 检查并发限制
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            self.logger.warning(f"达到并发限制 ({self.max_concurrent_tasks})，跳过任务: {task.name}")
            return

        # 创建执行记录
        execution_id = f"exec_{task.id}_{int(time.time())}"
        execution = TaskExecution(
            id=execution_id,
            task_id=task.id,
            started_at=datetime.now()
        )

        # 添加到运行列表
        self.running_tasks[task.id] = execution

        # 更新任务状态
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        self._update_task_in_db(task)

        # 提交到线程池执行
        future = self.executor.submit(self._run_task, task, execution)
        future.add_done_callback(lambda f: self._task_completed(task, execution, f))

        self.logger.info(f"开始执行任务: {task.name}")

    def _run_task(self, task: ScheduledTask, execution: TaskExecution) -> Dict[str, Any]:
        """运行任务的实际逻辑"""
        start_time = time.time()
        result = {
            'success': False,
            'records': [],
            'message': ''
        }

        try:
            if task.task_type == 'data_acquisition':
                result = self._execute_data_acquisition(task)
            elif task.task_type == 'quality_check':
                result = self._execute_quality_check(task)
            elif task.task_type == 'data_update':
                result = self._execute_data_update(task)
            else:
                raise ValueError(f"不支持的任务类型: {task.task_type}")

            execution.records_processed = len(result.get('records', []))
            execution.records_added = result.get('records_added', 0)
            execution.records_updated = result.get('records_updated', 0)
            execution.records_failed = result.get('records_failed', 0)

        except Exception as e:
            result['success'] = False
            result['message'] = str(e)
            result['error'] = str(e)
            self.logger.error(f"任务执行失败: {task.name}, 错误: {e}")

        finally:
            execution.execution_time = time.time() - start_time
            execution.status = TaskStatus.COMPLETED if result['success'] else TaskStatus.FAILED
            execution.result = result
            execution.error = result.get('error')

        return result

    def _execute_data_acquisition(self, task: ScheduledTask) -> Dict[str, Any]:
        """执行数据获取任务"""
        connector_config = task.connector_config
        parameters = task.parameters

        # 创建连接器
        if connector_config.get('type') == 'academic':
            connector = AcademicDatabaseConnector(connector_config)
        elif connector_config.get('type') == 'open_data':
            connector = OpenDataConnector(connector_config)
        else:
            raise ValueError(f"不支持的连接器类型: {connector_config.get('type')}")

        # 执行搜索
        query = parameters.get('query', '')
        max_results = parameters.get('max_results', 100)
        databases = parameters.get('databases')

        records = connector.search(query, databases=databases, max_results=max_results)

        # 保存记录
        saved_count = self._save_records(records, task.id)

        return {
            'success': True,
            'records': [asdict(record) for record in records],
            'records_added': saved_count,
            'message': f'成功获取 {len(records)} 条记录'
        }

    def _execute_quality_check(self, task: ScheduledTask) -> Dict[str, Any]:
        """执行质量检查任务"""
        # 获取待检查的记录
        records = self._get_pending_quality_check_records(task.parameters.get('limit', 100))

        if not records:
            return {
                'success': True,
                'records': [],
                'records_checked': 0,
                'message': '没有待检查的记录'
            }

        # 创建质量控制器
        quality_controller = DataQualityController(task.connector_config)

        checked_count = 0
        passed_count = 0

        for record in records:
            try:
                cleaned_data, quality_report, cleaning_actions = quality_controller.assess_and_clean(record)
                checked_count += 1
                if quality_report.overall_score >= task.parameters.get('quality_threshold', 0.7):
                    passed_count += 1

                # 更新记录状态
                self._update_record_quality_status(record['id'], quality_report.overall_score)

            except Exception as e:
                self.logger.error(f"质量检查失败 - 记录 {record.get('id')}: {e}")

        return {
            'success': True,
            'records': [],
            'records_checked': checked_count,
            'records_passed': passed_count,
            'message': f'检查了 {checked_count} 条记录，{passed_count} 条通过'
        }

    def _execute_data_update(self, task: ScheduledTask) -> Dict[str, Any]:
        """执行数据更新任务"""
        # 获取需要更新的记录
        records = self._get_records_for_update(task.parameters)

        updated_count = 0

        for record in records:
            try:
                # 重新获取最新数据
                connector_config = task.connector_config
                if connector_config.get('type') == 'academic':
                    connector = AcademicDatabaseConnector(connector_config)

                updated_record = connector.get_record(record.get('external_id'))
                if updated_record:
                    self._update_record(record['id'], asdict(updated_record))
                    updated_count += 1

            except Exception as e:
                self.logger.error(f"记录更新失败 - 记录 {record.get('id')}: {e}")

        return {
            'success': True,
            'records': [],
            'records_updated': updated_count,
            'message': f'更新了 {updated_count} 条记录'
        }

    def _task_completed(self, task: ScheduledTask, execution: TaskExecution, future):
        """任务完成回调"""
        try:
            # 获取执行结果
            result = future.result()

            # 更新执行记录
            execution.completed_at = datetime.now()
            execution.status = TaskStatus.COMPLETED if result['success'] else TaskStatus.FAILED

            # 保存执行记录
            self._save_execution(execution)

            # 更新任务状态
            if result['success']:
                task.status = TaskStatus.COMPLETED
                self.logger.info(f"任务完成: {task.name}")
            else:
                task.status = TaskStatus.FAILED
                self.logger.error(f"任务失败: {task.name}, 错误: {result.get('error')}")

                # 重试逻辑
                if execution.records_processed < task.max_retries:
                    task.status = TaskStatus.RETRYING
                    self._schedule_retry(task)

            self._update_task_in_db(task)

            # 从运行列表移除
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]

            # 执行回调
            self._execute_callbacks(task.id, execution)

        except Exception as e:
            self.logger.error(f"任务完成处理失败: {e}")

    def _schedule_retry(self, task: ScheduledTask):
        """安排任务重试"""
        retry_delay = task.retry_delay
        self.logger.info(f"安排任务重试: {task.name}, {retry_delay}秒后重试")

        def retry():
            time.sleep(retry_delay)
            if self.running and task.id in self.tasks:
                self._execute_task(task)

        threading.Thread(target=retry, daemon=True).start()

    def _cancel_running_task(self, task_id: str):
        """取消正在运行的任务"""
        if task_id in self.running_tasks:
            execution = self.running_tasks[task_id]
            execution.status = TaskStatus.CANCELLED
            execution.completed_at = datetime.now()
            self._save_execution(execution)
            del self.running_tasks[task_id]
            self.logger.info(f"取消任务: {task_id}")

    def _check_timeouts(self):
        """检查任务超时"""
        current_time = datetime.now()
        for task_id, execution in self.running_tasks.items():
            task = self.tasks.get(task_id)
            if task:
                elapsed = (current_time - execution.started_at).total_seconds()
                if elapsed > task.timeout:
                    self.logger.warning(f"任务超时: {task.name}")
                    self._cancel_running_task(task_id)

    def _cleanup_completed_tasks(self):
        """清理完成的任务"""
        # 定期清理旧的执行记录
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-500:]

    def _save_records(self, records: List[DataRecord], task_id: str) -> int:
        """保存记录"""
        # 这里应该实现实际的记录保存逻辑
        # 例如保存到数据库或文件
        return len(records)

    def _get_pending_quality_check_records(self, limit: int) -> List[Dict[str, Any]]:
        """获取待质量检查的记录"""
        # 这里应该实现获取记录的逻辑
        return []

    def _get_records_for_update(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取需要更新的记录"""
        # 这里应该实现获取记录的逻辑
        return []

    def _update_record_quality_status(self, record_id: str, quality_score: float):
        """更新记录质量状态"""
        # 这里应该实现更新记录状态的逻辑
        pass

    def _update_record(self, record_id: str, updated_data: Dict[str, Any]):
        """更新记录"""
        # 这里应该实现更新记录的逻辑
        pass

    def _save_execution(self, execution: TaskExecution):
        """保存执行记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO task_executions
            (id, task_id, started_at, completed_at, status, result, error,
             records_processed, records_added, records_updated, records_failed, execution_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            execution.id,
            execution.task_id,
            execution.started_at,
            execution.completed_at,
            execution.status.value,
            json.dumps(execution.result) if execution.result else None,
            execution.error,
            execution.records_processed,
            execution.records_added,
            execution.records_updated,
            execution.records_failed,
            execution.execution_time
        ))

        conn.commit()
        conn.close()

    def _update_task_in_db(self, task: ScheduledTask):
        """更新数据库中的任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE tasks SET
            last_run = ?, next_run = ?, status = ?, updated_at = ?
            WHERE id = ?
        ''', (
            task.last_run,
            task.next_run,
            task.status.value,
            datetime.now(),
            task.id
        ))

        conn.commit()
        conn.close()

    def _row_to_task(self, row) -> Optional[ScheduledTask]:
        """数据库行转换为任务对象"""
        try:
            return ScheduledTask(
                id=row[0],
                name=row[1],
                description=row[2],
                task_type=row[3],
                schedule=row[4],
                connector_config=json.loads(row[5]) if row[5] else {},
                parameters=json.loads(row[6]) if row[6] else {},
                priority=TaskPriority(row[7]),
                enabled=bool(row[8]),
                max_retries=row[9],
                retry_delay=row[10],
                timeout=row[11],
                last_run=datetime.fromisoformat(row[12]) if row[12] else None,
                next_run=datetime.fromisoformat(row[13]) if row[13] else None,
                status=TaskStatus(row[14]),
                created_at=datetime.fromisoformat(row[15]),
                updated_at=datetime.fromisoformat(row[16])
            )
        except Exception as e:
            self.logger.error(f"转换任务对象失败: {e}")
            return None

    def _row_to_execution(self, row) -> Optional[TaskExecution]:
        """数据库行转换为执行对象"""
        try:
            return TaskExecution(
                id=row[0],
                task_id=row[1],
                started_at=datetime.fromisoformat(row[2]),
                completed_at=datetime.fromisoformat(row[3]) if row[3] else None,
                status=TaskStatus(row[4]),
                result=json.loads(row[5]) if row[5] else None,
                error=row[6],
                records_processed=row[7] or 0,
                records_added=row[8] or 0,
                records_updated=row[9] or 0,
                records_failed=row[10] or 0,
                execution_time=row[11] or 0.0
            )
        except Exception as e:
            self.logger.error(f"转换执行对象失败: {e}")
            return None

    def _execute_callbacks(self, task_id: str, execution: TaskExecution):
        """执行任务回调"""
        if task_id in self.task_callbacks:
            for callback in self.task_callbacks[task_id]:
                try:
                    callback(execution)
                except Exception as e:
                    self.logger.error(f"执行回调失败: {e}")

class MonitoringService:
    """监控服务"""

    def __init__(self, scheduler: TaskScheduler, config: Dict[str, Any]):
        self.scheduler = scheduler
        self.config = config
        self.alert_thresholds = config.get('alert_thresholds', {
            'failure_rate': 0.3,  # 失败率阈值
            'execution_time': 3600,  # 执行时间阈值（秒）
            'queue_size': 10  # 队列大小阈值
        })
        self.notification_config = config.get('notifications', {})

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        current_time = datetime.now()

        # 基本统计
        total_tasks = len(self.scheduler.tasks)
        running_tasks = len(self.scheduler.running_tasks)
        enabled_tasks = sum(1 for task in self.scheduler.tasks.values() if task.enabled)

        # 最近24小时的执行统计
        recent_executions = self.scheduler.get_task_history(limit=100)
        recent_executions = [e for e in recent_executions
                           if (current_time - e.started_at).total_seconds() <= 86400]

        if recent_executions:
            successful_executions = sum(1 for e in recent_executions if e.status == TaskStatus.COMPLETED)
            failed_executions = sum(1 for e in recent_executions if e.status == TaskStatus.FAILED)
            avg_execution_time = sum(e.execution_time for e in recent_executions) / len(recent_executions)
        else:
            successful_executions = failed_executions = 0
            avg_execution_time = 0

        # 计算失败率
        failure_rate = failed_executions / len(recent_executions) if recent_executions else 0

        return {
            'timestamp': current_time.isoformat(),
            'tasks': {
                'total': total_tasks,
                'enabled': enabled_tasks,
                'running': running_tasks,
                'failed': sum(1 for task in self.scheduler.tasks.values() if task.status == TaskStatus.FAILED)
            },
            'executions': {
                'last_24h': {
                    'total': len(recent_executions),
                    'successful': successful_executions,
                    'failed': failed_executions,
                    'failure_rate': round(failure_rate, 3),
                    'avg_execution_time': round(avg_execution_time, 2)
                }
            },
            'alerts': self._check_alerts(failure_rate, avg_execution_time)
        }

    def _check_alerts(self, failure_rate: float, avg_execution_time: float) -> List[Dict[str, Any]]:
        """检查告警条件"""
        alerts = []

        # 失败率告警
        if failure_rate > self.alert_thresholds['failure_rate']:
            alerts.append({
                'type': 'failure_rate',
                'level': 'warning',
                'message': f"任务失败率过高: {failure_rate:.1%}",
                'threshold': self.alert_thresholds['failure_rate'],
                'current_value': failure_rate
            })

        # 执行时间告警
        if avg_execution_time > self.alert_thresholds['execution_time']:
            alerts.append({
                'type': 'execution_time',
                'level': 'warning',
                'message': f"平均执行时间过长: {avg_execution_time:.1f}秒",
                'threshold': self.alert_thresholds['execution_time'],
                'current_value': avg_execution_time
            })

        # 队列大小告警
        queue_size = len(self.scheduler.running_tasks)
        if queue_size > self.alert_thresholds['queue_size']:
            alerts.append({
                'type': 'queue_size',
                'level': 'warning',
                'message': f"运行队列过长: {queue_size}个任务",
                'threshold': self.alert_thresholds['queue_size'],
                'current_value': queue_size
            })

        return alerts

    def send_alert(self, alert: Dict[str, Any]):
        """发送告警通知"""
        if not self.notification_config.get('enabled', False):
            return

        message = f"🚨 系统告警\n{alert['message']}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # 这里可以实现不同的通知方式
        # 例如：邮件、短信、Slack、微信等

        logger.warning(f"告警: {alert['message']}")

# 导出主要类
__all__ = [
    'TaskScheduler',
    'MonitoringService',
    'ScheduledTask',
    'TaskExecution',
    'TaskStatus',
    'TaskPriority'
]