package com.human.backend;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

/** 관리자 가격 데이터 API의 빈 데이터 처리와 권한 차단을 검증합니다. */
@SpringBootTest
@org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
class AdminPriceDataIntegrationTests {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void adminCanReadEmptyPriceDataStatus() throws Exception {
        mockMvc.perform(get("/api/admin/price-data").with(user("admin").roles("ADMIN")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("NO_DATA"))
            .andExpect(jsonPath("$.totalPriceCount").value(0))
            .andExpect(jsonPath("$.totalSeriesCount").value(0))
            .andExpect(jsonPath("$.sources").isArray());
    }

    @Test
    void ordinaryUserCannotReadPriceDataStatus() throws Exception {
        mockMvc.perform(get("/api/admin/price-data").with(user("member").roles("USER")))
            .andExpect(status().isForbidden());
    }
}
