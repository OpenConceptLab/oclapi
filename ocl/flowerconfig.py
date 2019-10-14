from flower.utils.template import humanize

def format_task(task):
    task.args = humanize(task.args, length=1000)
    task.result = humanize(task.result, length=1000)
    return task