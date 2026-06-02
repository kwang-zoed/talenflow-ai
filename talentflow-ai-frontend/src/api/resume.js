// api/resume.js
import request from '../utils/request' // 假设你封装了一个 axios 实例在 utils/request.js

/**
 * 获取用户的简历列表
 * @returns {Promise}
 * 返回结构示例: { code: 200, data: [ { id: 1, name: '...', is_default: true }, ... ] }
 */
export const getResumeListAPI = () => {
  return request({
    url: '/resume/list',      // 对应后端路由
    method: 'GET'
  })
}

/**
 * 获取单份简历详情
 * @param {Number} id - 简历ID
 * @returns {Promise}
 */
export const getResumeDetailAPI = (id) => {
  return request({
    url: `/resume/${id}`,     // RESTful 风格
    method: 'GET'
  })
}

/**
 * 创建新简历
 * @param {Object} data - 简历数据对象 (如 title, content 等)
 * @returns {Promise}
 */
export const createResumeAPI = (data) => {
  return request({
    url: '/resume',
    method: 'POST',
    data
  })
}

/**
 * 更新简历信息
 * @param {Number} id - 简历ID
 * @param {Object} data - 需要更新的字段
 * @returns {Promise}
 */
export const updateResumeAPI = (id, data) => {
  return request({
    url: `/resume/${id}`,
    method: 'PUT',
    data
  })
}

/**
 * 删除简历
 * @param {Number} id - 简历ID
 * @returns {Promise}
 */
export const deleteResumeAPI = (id) => {
  return request({
    url: `/resume/${id}`,
    method: 'DELETE'
  })
}

/**
 * 设置默认简历
 * @param {Number} id - 简历ID
 * @returns {Promise}
 */
export const setDefaultResumeAPI = (id) => {
  return request({
    url: '/resume/default',
    method: 'POST',
    data: { resume_id: id } // 或者是 query 参数，视后端定义而定
  })
}

/**
 * 解析简历文件
 * @param {FormData} formData - 包含 file 字段的 FormData 对象
 */
export function parseResumeFileAPI(formData) {
  return request({
    url: '/resume/parse',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}