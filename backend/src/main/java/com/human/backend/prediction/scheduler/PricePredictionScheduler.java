package com.human.backend.prediction.scheduler;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.util.concurrent.atomic.AtomicBoolean;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import com.human.backend.prediction.dto.response.PricePredictionCollectionResult;
import com.human.backend.prediction.repository.PricePredictionRepository;
import com.human.backend.prediction.service.PricePredictionService;
import com.human.backend.price.repository.IngredientPriceRepository;

@Component
public class PricePredictionScheduler {

    private static final Logger log = LoggerFactory.getLogger(PricePredictionScheduler.class);

    private final PricePredictionService service;
    private final PricePredictionRepository predictionRepository;
    private final IngredientPriceRepository ingredientPriceRepository;
    private final TaskScheduler taskScheduler;
    private final boolean catchUpEnabled;
    private final Duration catchUpStartupDelay;
    private final int catchUpMaxLagDays;
    private final int retryMaxAttempts;
    private final Duration retryDelay;

    // 정기 실행·시작 시 보충 실행·재시도가 겹쳐 같은 예측을 동시에 만들지 않도록 막는다.
    private final AtomicBoolean running = new AtomicBoolean(false);

    public PricePredictionScheduler(
            PricePredictionService service,
            PricePredictionRepository predictionRepository,
            IngredientPriceRepository ingredientPriceRepository,
            TaskScheduler taskScheduler,
            @Value("${price.prediction.catchup.enabled:true}") boolean catchUpEnabled,
            @Value("${price.prediction.catchup.startup-delay:60s}") Duration catchUpStartupDelay,
            @Value("${price.prediction.catchup.max-lag-days:7}") int catchUpMaxLagDays,
            @Value("${price.prediction.retry.max-attempts:3}") int retryMaxAttempts,
            @Value("${price.prediction.retry.delay:10m}") Duration retryDelay) {
        if (catchUpMaxLagDays < 1) {
            throw new IllegalArgumentException("가격예측 보충 실행 기준 일수는 1일 이상이어야 합니다.");
        }
        if (retryMaxAttempts < 1) {
            throw new IllegalArgumentException("가격예측 최대 시도 횟수는 1회 이상이어야 합니다.");
        }
        this.service = service;
        this.predictionRepository = predictionRepository;
        this.ingredientPriceRepository = ingredientPriceRepository;
        this.taskScheduler = taskScheduler;
        this.catchUpEnabled = catchUpEnabled;
        this.catchUpStartupDelay = catchUpStartupDelay;
        this.catchUpMaxLagDays = catchUpMaxLagDays;
        this.retryMaxAttempts = retryMaxAttempts;
        this.retryDelay = retryDelay;
    }

    @Scheduled(
            cron = "${price.prediction.schedule.cron:0 0 3 * * MON}",
            zone = "${kamis.collection.schedule.zone:Asia/Seoul}")
    public void generateWeeklyPredictions() {
        generateWithRetry("정기 스케줄", 1);
    }

    /**
     * 정해진 시각에 서버가 꺼져 있으면 @Scheduled 실행은 사라지므로,
     * 서버가 다시 시작될 때 예측이 실제 가격보다 오래됐는지 확인해 한 번 보충 실행한다.
     */
    @EventListener(ApplicationReadyEvent.class)
    public void scheduleCatchUpAfterStartup() {
        if (!catchUpEnabled) {
            log.info("가격예측 시작 시 보충 실행이 꺼져 있습니다.");
            return;
        }
        // 서버 기동과 헬스체크를 먼저 끝낸 뒤 실행한다.
        taskScheduler.schedule(this::catchUpIfStale, Instant.now().plus(catchUpStartupDelay));
    }

    void catchUpIfStale() {
        try {
            LocalDate latestPriceDate = ingredientPriceRepository.findLatestPriceDate();
            if (latestPriceDate == null) {
                log.info("가격 데이터가 없어 가격예측 보충 실행을 건너뜁니다.");
                return;
            }
            LocalDate latestPredictionBaseDate = predictionRepository.findLatestWeeklyBaseDate();
            boolean upToDate = latestPredictionBaseDate != null
                    && !latestPredictionBaseDate.isBefore(latestPriceDate.minusDays(catchUpMaxLagDays));
            if (upToDate) {
                log.info("가격예측이 최신입니다. 보충 실행을 건너뜁니다. 최신 예측 기준일={}, 최신 가격일={}",
                        latestPredictionBaseDate, latestPriceDate);
                return;
            }
            log.warn("가격예측이 최신 가격보다 {}일 넘게 뒤처져 보충 실행합니다. 최신 예측 기준일={}, 최신 가격일={}",
                    catchUpMaxLagDays, latestPredictionBaseDate, latestPriceDate);
            generateWithRetry("시작 시 보충 실행", 1);
        } catch (RuntimeException exception) {
            log.error("가격예측 보충 실행 여부를 확인하지 못했습니다. 사유={}", exception.getMessage(), exception);
        }
    }

    void generateWithRetry(String trigger, int attempt) {
        if (!running.compareAndSet(false, true)) {
            log.warn("주간 가격예측이 이미 실행 중이어서 건너뜁니다. 실행 원인={}", trigger);
            return;
        }

        boolean failed = false;
        Instant startedAt = Instant.now();
        long startedNanos = System.nanoTime();
        log.info("주간 가격예측 생성을 시작합니다. 실행 원인={}, 시도={}/{}, 실행 시작 시각={}",
                trigger, attempt, retryMaxAttempts, startedAt);
        try {
            PricePredictionCollectionResult result = service.generateSevenDayPredictions();
            log.info(
                    "주간 가격예측 생성을 완료했습니다. 실행 원인={}, 실행 시작 시각={}, 소요 시간={}ms, "
                            + "대상={}, 응답={}, 신규 저장={}, 중복 제외={}",
                    trigger, startedAt, elapsedMillis(startedNanos), result.requestedSeries(),
                    result.receivedPredictions(), result.insertedPredictions(),
                    result.duplicatesSkipped());
        } catch (RuntimeException exception) {
            failed = true;
            log.error(
                    "주간 가격예측 생성에 실패했습니다. 실행 원인={}, 시도={}/{}, 실행 시작 시각={}, "
                            + "소요 시간={}ms, 사유={}",
                    trigger, attempt, retryMaxAttempts, startedAt, elapsedMillis(startedNanos),
                    exception.getMessage(), exception);
        } finally {
            running.set(false);
        }

        if (!failed) {
            return;
        }
        if (attempt >= retryMaxAttempts) {
            log.error("주간 가격예측 재시도 횟수를 모두 사용했습니다. 다음 정기 실행 또는 서버 재시작 때 다시 시도합니다.");
            return;
        }
        log.warn("주간 가격예측을 {} 뒤에 다시 시도합니다. 다음 시도={}/{}", retryDelay, attempt + 1, retryMaxAttempts);
        taskScheduler.schedule(
                () -> generateWithRetry(trigger, attempt + 1), Instant.now().plus(retryDelay));
    }

    private long elapsedMillis(long startedNanos) {
        return (System.nanoTime() - startedNanos) / 1_000_000L;
    }
}
