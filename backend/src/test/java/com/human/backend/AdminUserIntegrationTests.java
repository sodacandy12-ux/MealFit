package com.human.backend;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

/** 회원 관리자 목록 API가 관리자에게만 열리는지 확인합니다. */
@SpringBootTest
@org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
class AdminUserIntegrationTests {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void adminCanReadUserList() throws Exception {
        mockMvc.perform(get("/api/admin/users").with(user("admin").roles("ADMIN")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());
    }

    @Test
    void ordinaryUserCannotReadUserList() throws Exception {
        mockMvc.perform(get("/api/admin/users").with(user("member").roles("USER")))
            .andExpect(status().isForbidden());
    }
}
